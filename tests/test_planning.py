from datetime import datetime

import pytest

from bupt_agent import planning
from bupt_agent.common import SHANGHAI, AgentError, success
from bupt_agent.planning import candidate_windows, exam_busy_slots


def test_exam_half_open_intersection():
    busy = exam_busy_slots([{"time_text": "2026-11-03 09:35-10:10"}], "2026-11-03")
    assert busy == {3}


def test_pending_exam_does_not_look_free():
    with pytest.raises(AgentError) as error:
        exam_busy_slots([{"time_text": "日期待定"}], "2026-11-03")
    assert error.value.code == "EXAM_TIME_UNRESOLVED"


def test_windows_require_consecutive_available_periods_and_future_start():
    rooms = [{"name": "合成教室", "available_slots": [1, 2, 3, 4, 5, 6]}]
    result = candidate_windows(rooms, {3}, 2, 600)
    assert [r["slots"] for r in result] == [[4, 5], [5, 6]]


async def test_study_candidates_can_be_read_beyond_first_page(monkeypatch):
    class AcademicStub:
        async def schedule(self, _):
            return success({"items": []}, "synthetic")

        async def exams(self):
            return success({"items": []}, "synthetic")

        async def classrooms(self, **kwargs):
            return success(
                {"rooms": [{"name": "合成教室", "available_slots": [1, 2, 3]}]}, "synthetic"
            )

    monkeypatch.setattr(planning, "now", lambda: datetime(2026, 11, 3, tzinfo=SHANGHAI))
    first = await planning.study_slots(AcademicStub(), limit=1)
    second = await planning.study_slots(AcademicStub(), offset=1, limit=1)
    assert first["data"]["next_offset"] == 1
    assert second["data"]["next_offset"] is None
    assert first["data"]["candidates"][0]["slots"] == [1, 2]
    assert second["data"]["candidates"][0]["slots"] == [2, 3]
    assert not first["meta"]["complete"]
