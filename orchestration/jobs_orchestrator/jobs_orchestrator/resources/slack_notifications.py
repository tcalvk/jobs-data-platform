"""Reusable, optional Slack Incoming Webhook delivery for Dagster assets."""

from __future__ import annotations

import json
import os
from urllib import error, request
from urllib.parse import urlsplit

from dagster import ConfigurableResource


SLACK_WEBHOOK_HOSTS = frozenset({"hooks.slack.com", "hooks.slack-gov.com"})


class SlackNotificationError(RuntimeError):
    """A sanitized Slack delivery error safe to report in orchestrator logs."""


class _RejectRedirectHandler(request.HTTPRedirectHandler):
    """Refuse redirects so the webhook secret and payload are never forwarded."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SlackNotificationError("Slack webhook redirect was refused.")


def _validated_webhook_url(environment_variable: str) -> str:
    """Load a standard Slack Incoming Webhook URL without exposing it in errors."""
    webhook_url = os.getenv(environment_variable, "").strip()
    try:
        if not webhook_url or "\\" in webhook_url or any(
            ord(character) <= 32 or ord(character) == 127
            for character in webhook_url
        ):
            raise ValueError
        parsed = urlsplit(webhook_url)
        hostname = parsed.hostname
        port = parsed.port
        username = parsed.username
        password = parsed.password
        path_parts = parsed.path.split("/")
        if (
            parsed.scheme != "https"
            or hostname not in SLACK_WEBHOOK_HOSTS
            or port not in {None, 443}
            or username is not None
            or password is not None
            or parsed.query
            or parsed.fragment
            or len(path_parts) != 5
            or path_parts[0] != ""
            or path_parts[1] != "services"
            or not all(path_parts[2:])
        ):
            raise ValueError
    except (UnicodeError, ValueError):
        raise SlackNotificationError(
            "Slack webhook configuration is missing or invalid."
        ) from None
    return webhook_url


class SlackNotificationsResource(ConfigurableResource):
    """Best-effort-capable Incoming Webhook delivery configured by environment.

    Callers own message policy and decide how to handle delivery errors. When the
    resource is disabled, ``send_message`` is a no-op and returns ``False``.
    """

    enabled: bool = False
    webhook_url_env_var: str = "SLACK_WEBHOOK_URL"
    timeout_seconds: float = 3.0

    def send_message(self, message: str) -> bool:
        """Post plain message text, returning true when Slack accepts it."""
        if not self.enabled:
            return False
        if not 0 < self.timeout_seconds <= 10:
            raise SlackNotificationError(
                "Slack notification timeout must be greater than zero and at most 10 seconds."
            )
        webhook_url = _validated_webhook_url(self.webhook_url_env_var)
        payload = json.dumps({"text": message}).encode("utf-8")

        try:
            webhook_request = request.Request(
                webhook_url,
                data=payload,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            opener = request.build_opener(_RejectRedirectHandler())
            with opener.open(webhook_request, timeout=self.timeout_seconds) as response:
                status = response.status
                body = response.read(1024)
        except SlackNotificationError:
            raise
        except error.HTTPError as exc:
            raise SlackNotificationError(
                f"Slack webhook returned HTTP status {exc.code}."
            ) from None
        except (error.URLError, TimeoutError, OSError, ValueError):
            raise SlackNotificationError(
                "Slack request failed before a successful response was confirmed."
            ) from None

        if not 200 <= status < 300:
            raise SlackNotificationError(
                f"Slack webhook returned HTTP status {status}."
            )
        try:
            accepted = body.decode("utf-8").strip() == "ok"
        except UnicodeDecodeError:
            accepted = False
        if not accepted:
            # Never include Slack's unrestricted response text in errors or logs.
            raise SlackNotificationError("Slack webhook did not accept the notification.")
        return True
