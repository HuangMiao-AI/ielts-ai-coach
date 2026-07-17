"""IELTS score analysis and personalized recommendation rules."""

from decimal import Decimal, ROUND_HALF_UP

from config import SUBJECTS
from models import AnalysisResult


RECOMMENDATIONS: dict[str, list[str]] = {
    "listening": [
        "每天精听一段 2–3 分钟的雅思材料：先盲听，再对照原文，最后跟读。",
        "建立错词本，重点记录连读、弱读、数字、日期和同义替换。",
        "每周至少完成两次限时 Section 3 或 Section 4 训练。",
    ],
    "reading": [
        "练习先读题干并圈出关键词，再回原文定位同义替换。",
        "按题型整理错题，优先突破判断题、段落匹配等失分较多的类型。",
        "训练 20 分钟完成一篇文章，结束后必须分析每道错题的原因。",
    ],
    "writing": [
        "先搭建常用结构：Task 1 按特征分组，Task 2 保持观点和段落逻辑一致。",
        "每次写作后检查任务回应、衔接、词汇和语法四项评分标准。",
        "积累能准确使用的主题词组，避免为了高级而使用不熟悉的表达。",
    ],
    "speaking": [
        "每天选择一个话题录音 2 分钟，回听并标记停顿、重复和语法错误。",
        "使用“观点—原因—例子”的三步结构扩展 Part 2 和 Part 3 回答。",
        "跟读自然英语材料，模仿重音和语调，不需要刻意追求某种口音。",
    ],
}


def _validate_scores(scores: dict[str, float]) -> None:
    missing = set(SUBJECTS) - set(scores)
    if missing:
        raise ValueError(f"缺少科目成绩：{', '.join(sorted(missing))}")

    for subject in SUBJECTS:
        score = scores[subject]
        if not 0.0 <= score <= 9.0:
            raise ValueError(f"{subject} 成绩必须在 0 到 9 之间。")


def calculate_overall_band(scores: dict[str, float]) -> float:
    """Calculate the IELTS overall band, rounded to the nearest half band."""

    _validate_scores(scores)
    total = sum(Decimal(str(scores[subject])) for subject in SUBJECTS)
    average = total / Decimal(len(SUBJECTS))
    rounded = (average * 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / 2
    return float(rounded)


def analyze_scores(scores: dict[str, float]) -> AnalysisResult:
    """Find all lowest-scoring subjects and return focused advice."""

    _validate_scores(scores)
    lowest_score = min(scores[subject] for subject in SUBJECTS)
    lowest_subjects = tuple(
        subject for subject in SUBJECTS if scores[subject] == lowest_score
    )

    return AnalysisResult(
        overall_band=calculate_overall_band(scores),
        lowest_score=float(lowest_score),
        lowest_subjects=lowest_subjects,
        recommendations={
            subject: RECOMMENDATIONS[subject] for subject in lowest_subjects
        },
    )
