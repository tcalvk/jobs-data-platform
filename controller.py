#!/usr/bin/env python3
"""
Cloud Run Job dispatcher.

Usage:
  python run.py <task>

Or set:
  JOB_TASK=<task>

Examples:
  python run.py serpapi
  JOB_TASK=serpapi python run.py
"""

from __future__ import annotations

import importlib
import logging
import os
import sys
import time
from typing import Callable, Dict


def setup_logging() -> None:
    # Cloud Run picks up stdout/stderr; keep it simple/structured.
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def get_task_name(argv: list[str]) -> str | None:
    # Priority: CLI arg > env var
    if len(argv) >= 2 and argv[1].strip():
        return argv[1].strip()
    env_task = os.getenv("JOB_TASK", "").strip()
    return env_task or None


def load_callable(module_path: str, func_name: str = "main") -> Callable[[], int]:
    """
    Import module and return its callable `main` function.
    main() should return an int exit code (0 ok) or raise.
    """
    mod = importlib.import_module(module_path)
    fn = getattr(mod, func_name, None)
    if not callable(fn):
        raise AttributeError(f"Module '{module_path}' does not define callable '{func_name}()'")
    return fn


def usage(tasks: Dict[str, str]) -> str:
    task_list = "\n".join([f"  - {k}" for k in sorted(tasks.keys())])
    return (
        "Missing/invalid task.\n\n"
        "Run with: python run.py <task>\n"
        "Or set:   JOB_TASK=<task>\n\n"
        f"Available tasks:\n{task_list}\n"
    )


def main(argv: list[str]) -> int:
    setup_logging()
    log = logging.getLogger("run")

    # Map task name -> module path (each module exposes main()).
    # Example module layout:
    #   jobs_data_platform/ingest/serpapi.py   -> main()
    #   jobs_data_platform/ingest/google.py    -> main()
    TASKS: Dict[str, str] = {
        "serpapi_get_jobs": "jobs_data_platform.ingest.serpapi_get_jobs",
        "gcs_to_bq_load": "jobs_data_platform.ao.gcs_to_bq_load",
        #"google_jobs": "jobs_data_platform.ingest.google_jobs",
        # add more here...
        # "linkedin": "jobs_data_platform.ingest.linkedin",
    }

    task = get_task_name(argv)
    if not task or task not in TASKS:
        sys.stderr.write(usage(TASKS))
        return 2

    module_path = TASKS[task]
    log.info("Starting task '%s' (%s)", task, module_path)

    started = time.time()
    try:
        fn = load_callable(module_path, "main")
        # Convention: main() returns 0 on success, non-zero on failure.
        rc = fn()
        rc = 0 if rc is None else int(rc)
        elapsed = round(time.time() - started, 3)
        if rc == 0:
            log.info("Task '%s' succeeded in %ss", task, elapsed)
        else:
            log.error("Task '%s' failed with exit code %s in %ss", task, rc, elapsed)
        return rc
    except Exception:
        elapsed = round(time.time() - started, 3)
        log.exception("Task '%s' crashed after %ss", task, elapsed)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))