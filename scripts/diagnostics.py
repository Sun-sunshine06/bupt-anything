"""Small allowlisted outputs for account-backed diagnostic scripts."""

import asyncio
import json
import re
import sys


def error_code(value):
    code = value.get("code") if isinstance(value, dict) else None
    return (
        code
        if isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", code)
        else "DIAGNOSTIC_FAILED"
    )


def summary(name, result):
    item = {"tool": name, "ok": result.get("ok") is True}
    if item["ok"]:
        item["complete"] = result.get("meta", {}).get("complete") is True
        data = result.get("data")
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            item["sample_count"] = len(data["items"])
    else:
        item["error_code"] = error_code(result.get("error"))
    return item


def run(main):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        return_code = asyncio.run(main())
    except (Exception, KeyboardInterrupt):
        print(json.dumps({"ok": False, "error_code": "DIAGNOSTIC_FAILED"}), flush=True)
        return_code = 1
    raise SystemExit(return_code or 0)
