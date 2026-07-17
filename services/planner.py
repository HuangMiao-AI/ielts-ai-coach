"""Generate a practical daily and weekly study plan."""

from typing import Any

from config import SUBJECT_LABELS, SUBJECTS


ACTIVITIES = {
    "listening": "精听、听写与跟读",
    "reading": "限时阅读与错题定位",
    "writing": "提纲训练与段落写作",
    "speaking": "话题录音与复述",
}


def _allocate_minutes(total: int, weights: list[int]) -> list[int]:
    """Allocate all available minutes while keeping every block usable."""

    raw = [total * weight / sum(weights) for weight in weights]
    allocated = [int(value) for value in raw]
    for index in range(total - sum(allocated)):
        allocated[index % len(allocated)] += 1
    return allocated


def generate_study_plan(
    daily_minutes: int, lowest_subjects: tuple[str, ...]
) -> dict[str, Any]:
    """Build a seven-day plan centered on the student's weakest subject(s)."""

    if not 30 <= daily_minutes <= 360:
        raise ValueError("每日学习时间必须在 30 到 360 分钟之间。")
    if not lowest_subjects or any(subject not in SUBJECTS for subject in lowest_subjects):
        raise ValueError("最低分科目无效。")

    focus_labels = "、".join(SUBJECT_LABELS[item] for item in lowest_subjects)
    focus_activities = " + ".join(ACTIVITIES[item] for item in lowest_subjects)
    minutes = _allocate_minutes(daily_minutes, [15, 50, 25, 10])

    daily_blocks = [
        {
            "title": "热身复习",
            "minutes": minutes[0],
            "detail": "复习昨天的错题和高频词组，快速进入学习状态。",
        },
        {
            "title": f"弱项主攻：{focus_labels}",
            "minutes": minutes[1],
            "detail": f"完成{focus_activities}，记录错误原因和可复用的方法。",
        },
        {
            "title": "四科轮换训练",
            "minutes": minutes[2],
            "detail": "从其他科目中选择一项限时练习，保持综合能力。",
        },
        {
            "title": "复盘收尾",
            "minutes": minutes[3],
            "detail": "写下今天的 1 个进步、1 个问题和明天的重点。",
        },
    ]

    rotating_subjects = [
        subject for subject in SUBJECTS if subject not in lowest_subjects
    ] or list(SUBJECTS)
    weekly_templates = [
        ("周一", f"{focus_labels}基础方法", "不计时，先保证方法正确"),
        ("周二", f"{focus_labels}专项训练", "完成一组题并逐题复盘"),
        (
            "周三",
            f"{SUBJECT_LABELS[rotating_subjects[0]]}轮换巩固",
            "保持优势科目手感",
        ),
        ("周四", f"{focus_labels}限时训练", "按考试时间完成并统计正确率"),
        (
            "周五",
            f"{SUBJECT_LABELS[rotating_subjects[-1]]}轮换巩固",
            "整理一周出现的共性问题",
        ),
        ("周六", "四科模拟与重点订正", "模拟后只精改最有价值的错题"),
        ("周日", "轻量复习与下周规划", "复习错题本，设定下周一个小目标"),
    ]

    weekly_plan = [
        {"day": day, "focus": focus, "goal": goal, "minutes": daily_minutes}
        for day, focus, goal in weekly_templates
    ]

    return {
        "focus_subjects": list(lowest_subjects),
        "daily_minutes": daily_minutes,
        "daily_blocks": daily_blocks,
        "weekly_plan": weekly_plan,
    }
