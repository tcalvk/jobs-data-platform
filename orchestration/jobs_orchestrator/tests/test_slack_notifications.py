import io
import json
import os
import unittest
from unittest.mock import MagicMock, patch
from urllib import error, request

import jobs_orchestrator.resources.slack_notifications as slack_module
from jobs_orchestrator.resources.slack_notifications import (
    SlackNotificationError,
    SlackNotificationsResource,
)


class SlackNotificationsResourceTests(unittest.TestCase):
    webhook_url = (
        "https://hooks.slack.com/services/"
        "T_PLACEHOLDER/B_PLACEHOLDER/WEBHOOK_SECRET_PLACEHOLDER"
    )
    webhook_secret = "WEBHOOK_SECRET_PLACEHOLDER"

    def _environment(self, webhook_url=None):
        return patch.dict(
            os.environ,
            {
                "SLACK_WEBHOOK_URL": (
                    self.webhook_url if webhook_url is None else webhook_url
                )
            },
        )

    @staticmethod
    def _response(body: bytes, status: int = 200):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = status
        response.read.return_value = body
        return response

    def test_disabled_configuration_is_no_op(self):
        resource = SlackNotificationsResource(enabled=False)

        with self._environment(webhook_url=""), patch.object(
            slack_module.request, "build_opener"
        ) as build_opener:
            attempted = resource.send_message("not sent")

        self.assertFalse(attempted)
        build_opener.assert_not_called()

    def test_missing_or_invalid_webhook_url_fails_without_http_attempt(self):
        invalid_urls = (
            "",
            "http://hooks.slack.com/services/T/B/secret-placeholder",
            "https://slack.com/services/T/B/secret-placeholder",
            "https://hooks.slack.com/not-services/T/B/secret-placeholder",
            "https://user:password@hooks.slack.com/services/T/B/secret-placeholder",
            "https://hooks.slack.com:444/services/T/B/secret-placeholder",
            "https://hooks.slack.com/services/T/B/secret-placeholder?query=value",
            "https://hooks.slack.com/services/T/B/secret-placeholder#fragment",
            "https://[::1/services/T/B/secret-placeholder",
        )
        for webhook_url in invalid_urls:
            with self.subTest(webhook_url=webhook_url), self._environment(
                webhook_url=webhook_url
            ), patch.object(
                slack_module.request, "build_opener"
            ) as build_opener, self.assertRaises(SlackNotificationError) as raised:
                SlackNotificationsResource(enabled=True).send_message("message")

            error_text = str(raised.exception)
            self.assertEqual(
                error_text, "Slack webhook configuration is missing or invalid."
            )
            if webhook_url:
                self.assertNotIn(webhook_url, error_text)
            build_opener.assert_not_called()

    def test_webhook_path_requires_exactly_three_components_after_services(self):
        valid_urls = (
            "https://hooks.slack.com/services/T_PLACEHOLDER/B_PLACEHOLDER/secret-placeholder",
            "https://hooks.slack-gov.com/services/T_PLACEHOLDER/B_PLACEHOLDER/secret-placeholder",
        )
        invalid_urls = (
            "https://hooks.slack.com/services",
            "https://hooks.slack.com/services/T_PLACEHOLDER",
            "https://hooks.slack.com/services/T_PLACEHOLDER/B_PLACEHOLDER",
            "https://hooks.slack.com/services/T_PLACEHOLDER/B_PLACEHOLDER/secret-placeholder/extra",
            "https://hooks.slack.com/services/T_PLACEHOLDER/B_PLACEHOLDER/secret-placeholder/",
        )

        for webhook_url in valid_urls:
            with self.subTest(webhook_url=webhook_url), self._environment(
                webhook_url=webhook_url
            ):
                self.assertEqual(
                    slack_module._validated_webhook_url("SLACK_WEBHOOK_URL"),
                    webhook_url,
                )

        for webhook_url in invalid_urls:
            with self.subTest(webhook_url=webhook_url), self._environment(
                webhook_url=webhook_url
            ), self.assertRaises(SlackNotificationError) as raised:
                slack_module._validated_webhook_url("SLACK_WEBHOOK_URL")

            self.assertEqual(
                str(raised.exception),
                "Slack webhook configuration is missing or invalid.",
            )
            self.assertNotIn(webhook_url, str(raised.exception))

    def test_standard_and_gov_slack_webhook_urls_are_accepted(self):
        valid_urls = (
            self.webhook_url,
            "https://hooks.slack.com:443/services/T_PLACEHOLDER/B_PLACEHOLDER/secret-placeholder",
            "https://hooks.slack-gov.com/services/T_PLACEHOLDER/B_PLACEHOLDER/secret-placeholder",
        )
        for webhook_url in valid_urls:
            with self.subTest(webhook_url=webhook_url), self._environment(
                webhook_url=webhook_url
            ):
                self.assertEqual(
                    slack_module._validated_webhook_url("SLACK_WEBHOOK_URL"),
                    webhook_url,
                )

    def test_plain_ok_success_posts_incoming_webhook_payload_and_timeout(self):
        resource = SlackNotificationsResource(enabled=True, timeout_seconds=2.5)
        opener = MagicMock()
        response = self._response(b"ok\n")
        opener.open.return_value = response

        with self._environment(), patch.object(
            slack_module.request, "build_opener", return_value=opener
        ) as build_opener:
            sent = resource.send_message("rejection summary")

        self.assertTrue(sent)
        redirect_handler = build_opener.call_args.args[0]
        self.assertIsInstance(redirect_handler, slack_module._RejectRedirectHandler)
        webhook_request = opener.open.call_args.args[0]
        self.assertEqual(webhook_request.full_url, self.webhook_url)
        self.assertEqual(webhook_request.method, "POST")
        self.assertIsNone(webhook_request.get_header("Authorization"))
        self.assertEqual(
            webhook_request.get_header("Content-type"),
            "application/json; charset=utf-8",
        )
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 2.5)
        self.assertEqual(
            json.loads(webhook_request.data),
            {"text": "rejection summary"},
        )
        response.read.assert_called_once_with(1024)

    def test_non_ok_body_uses_sanitized_error(self):
        unrestricted_response = "private-unrestricted-response"
        opener = MagicMock()
        opener.open.return_value = self._response(unrestricted_response.encode())

        with self._environment(), patch.object(
            slack_module.request, "build_opener", return_value=opener
        ), self.assertRaises(SlackNotificationError) as raised:
            SlackNotificationsResource(enabled=True).send_message("message")

        error_text = str(raised.exception)
        self.assertEqual(error_text, "Slack webhook did not accept the notification.")
        self.assertNotIn(unrestricted_response, error_text)
        self.assertNotIn(self.webhook_secret, error_text)

    def test_non_2xx_failure_uses_only_sanitized_status(self):
        unrestricted_response = b"raw-private-response"
        opener = MagicMock()
        opener.open.side_effect = error.HTTPError(
            self.webhook_url,
            503,
            "raw-private-reason",
            hdrs=None,
            fp=io.BytesIO(unrestricted_response),
        )

        with self._environment(), patch.object(
            slack_module.request, "build_opener", return_value=opener
        ), self.assertRaises(SlackNotificationError) as raised:
            SlackNotificationsResource(enabled=True).send_message("message")

        error_text = str(raised.exception)
        self.assertEqual(error_text, "Slack webhook returned HTTP status 503.")
        self.assertNotIn("raw-private", error_text)
        self.assertNotIn(self.webhook_secret, error_text)
        self.assertNotIn(self.webhook_url, error_text)

    def test_transport_failure_does_not_expose_url_or_underlying_reason(self):
        opener = MagicMock()
        opener.open.side_effect = error.URLError(
            f"private transport details containing {self.webhook_url}"
        )

        with self._environment(), patch.object(
            slack_module.request, "build_opener", return_value=opener
        ), self.assertRaises(SlackNotificationError) as raised:
            SlackNotificationsResource(enabled=True).send_message("message")

        error_text = str(raised.exception)
        self.assertEqual(
            error_text,
            "Slack request failed before a successful response was confirmed.",
        )
        self.assertNotIn(self.webhook_secret, error_text)
        self.assertNotIn(self.webhook_url, error_text)
        self.assertNotIn("private transport", error_text)

    def test_invalid_timeout_fails_without_reading_webhook_configuration(self):
        for timeout in (0, -1, 10.1, float("nan")):
            with self.subTest(timeout=timeout), self._environment(
                webhook_url=""
            ), patch.object(
                slack_module.request, "build_opener"
            ) as build_opener, self.assertRaises(SlackNotificationError) as raised:
                SlackNotificationsResource(
                    enabled=True, timeout_seconds=timeout
                ).send_message("message")

            self.assertIn("timeout", str(raised.exception))
            self.assertNotIn(self.webhook_secret, str(raised.exception))
            build_opener.assert_not_called()

    def test_redirect_handler_refuses_secret_url_and_payload_forwarding(self):
        original_request = request.Request(
            self.webhook_url,
            data=b'{"text":"private payload"}',
            method="POST",
        )
        handler = slack_module._RejectRedirectHandler()

        with self.assertRaises(SlackNotificationError) as raised:
            handler.redirect_request(
                original_request,
                fp=None,
                code=302,
                msg="private redirect response",
                headers={},
                newurl="https://untrusted.example/collect-secret",
            )

        error_text = str(raised.exception)
        self.assertEqual(error_text, "Slack webhook redirect was refused.")
        self.assertNotIn(self.webhook_secret, error_text)
        self.assertNotIn(self.webhook_url, error_text)
        self.assertNotIn("private payload", error_text)
        self.assertNotIn("untrusted.example", error_text)


if __name__ == "__main__":
    unittest.main()
