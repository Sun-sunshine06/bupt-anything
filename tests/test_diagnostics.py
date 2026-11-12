import json
import runpy
from pathlib import Path

import pytest

HELPERS = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/diagnostics.py"))


def test_summary_does_not_emit_content_identifiers_or_error_messages():
    summary = HELPERS["summary"]
    secret = "SENSITIVE-STUDENT-CONTENT"
    result = summary(
        "ucloud.assignments",
        {
            "ok": True,
            "data": {"items": [{"id": secret, "content": secret}]},
            "meta": {"complete": False, "source": secret},
        },
    )
    assert result == {
        "tool": "ucloud.assignments",
        "ok": True,
        "complete": False,
        "sample_count": 1,
    }
    failure = summary(
        "ucloud.assignments", {"ok": False, "error": {"code": "FORBIDDEN", "message": secret}}
    )
    assert secret not in json.dumps(failure)
    assert failure["error_code"] == "FORBIDDEN"
    assert HELPERS["error_code"]({"code": "token=private-value"}) == "DIAGNOSTIC_FAILED"


def test_unexpected_exception_is_not_printed(capsys):
    async def fail():
        raise RuntimeError("private-token and raw response")

    with pytest.raises(SystemExit) as exit_info:
        HELPERS["run"](fail)
    assert exit_info.value.code == 1
    output = capsys.readouterr()
    assert json.loads(output.out) == {"ok": False, "error_code": "DIAGNOSTIC_FAILED"}
    assert output.err == ""
