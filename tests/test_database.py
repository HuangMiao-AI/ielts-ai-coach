from pathlib import Path

from database import get_recent_records, save_study_record
from services.analysis import analyze_scores
from services.planner import generate_study_plan


def test_save_and_read_record(tmp_path: Path) -> None:
    database_path = tmp_path / "test_study_coach.db"
    scores = {"listening": 6.5, "reading": 6.0, "writing": 5.5, "speaking": 6.0}
    analysis = analyze_scores(scores)
    plan = generate_study_plan(90, analysis.lowest_subjects)

    record_id = save_study_record(
        "测试学生", scores, analysis, 90, plan, database_path=database_path
    )
    records = get_recent_records(database_path=database_path)

    assert record_id == 1
    assert len(records) == 1
    assert records[0].student_name == "测试学生"
    assert records[0].lowest_subjects == ["writing"]
    assert records[0].study_plan["daily_minutes"] == 90
