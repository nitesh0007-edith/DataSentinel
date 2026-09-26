from __future__ import annotations

"""LOCAL screenshot fixture: one real repository-test failure after apply.

Never use as a deployment entrypoint. Uses an isolated temporary runtime and
patches only the test runner, as the existing rollback regression tests do.
"""

import os
import tempfile
from pathlib import Path

import _bootstrap  # noqa: F401

runtime = Path(tempfile.mkdtemp(prefix="datasentinel-screenshots-"))
os.environ["DATASENTINEL_HOME"] = str(runtime)
os.environ["DATASENTINEL_WORKSPACE_DIR"] = str(runtime / "workspace")
os.environ["LLM_PROVIDER"] = "heuristic"
os.environ["DATASENTINEL_CORS_ORIGINS"] = '["http://localhost:3010","http://127.0.0.1:3010"]'

from app.core.config import get_settings
from app.core.models import ValidationCheck
from app.validation import validator

get_settings.cache_clear()
real_tests = validator.run_repository_tests
failed_once = False


def fail_once(settings):
    global failed_once
    if not failed_once:
        failed_once = True
        return ValidationCheck(
            name="Repository tests",
            passed=False,
            detail="DEMO FIXTURE: deliberately injected repository-test failure (local capture only).",
        )
    return real_tests(settings)


validator.run_repository_tests = fail_once

if __name__ == "__main__":
    import uvicorn

    print(f"LOCAL SCREENSHOT FIXTURE — isolated runtime: {runtime}")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8010, workers=1)
