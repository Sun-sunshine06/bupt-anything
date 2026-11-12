import json

from conftest import MemoryCredentials

from bupt_agent.app import App


async def test_missing_credentials_and_validation_are_explicit():
    app = App(credentials=MemoryCredentials(False))
    try:
        result = await app.invoke("ucloud.courses")
        assert not result["ok"] and result["error"]["code"] == "NOT_CONFIGURED"
        result = await app.invoke("academic.classrooms", {"slots": ["private-input"]})
        assert result["error"]["code"] == "INVALID_INPUT"
        assert "private-input" not in json.dumps(result)
        result = await app.invoke("ucloud.courses", {"password": "private-secret"})
        assert not result["ok"] and "private-secret" not in json.dumps(result)
    finally:
        await app.close()


async def test_attendance_discoverable_and_requires_credentials():
    app = App(credentials=MemoryCredentials(False))
    try:
        catalogue = {t["name"]: t for t in app.catalogue()}
        assert catalogue["attendance.current"]["read_only"]
        assert catalogue["attendance.list"]["read_only"]
        removed = {
            "attendance.submit",
            "attendance.qr",
            "qr.parse",
            "qr.decode",
            "qr.generate",
            "qr.build",
        }
        assert removed.isdisjoint(catalogue)
        for name in removed:
            result = await app.invoke(name)
            assert result["error"]["code"] == "UNKNOWN_TOOL"
        result = await app.invoke("attendance.current")
        assert result["error"]["code"] == "NOT_CONFIGURED"
        result = await app.invoke("attendance.list", {"course_id": "123"})
        assert result["error"]["code"] == "NOT_CONFIGURED"
    finally:
        await app.close()
