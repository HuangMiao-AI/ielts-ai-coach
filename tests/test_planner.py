from services.planner import generate_study_plan


def test_daily_blocks_use_all_available_minutes() -> None:
    plan = generate_study_plan(95, ("writing",))
    assert sum(block["minutes"] for block in plan["daily_blocks"]) == 95
    assert len(plan["weekly_plan"]) == 7


def test_plan_supports_tied_lowest_subjects() -> None:
    plan = generate_study_plan(60, ("writing", "speaking"))
    assert plan["focus_subjects"] == ["writing", "speaking"]
    assert "写作、口语" in plan["daily_blocks"][1]["title"]
