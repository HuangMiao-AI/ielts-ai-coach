"""Structured prompt, repair, and validation for IELTS writing feedback."""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from ielts_ai_coach.ai.base import AIProvider, AIProviderError
from ielts_ai_coach.ai.schemas import WritingFeedbackSchema
from ielts_ai_coach.database.models import Essay


WRITING_DISCLAIMER = "该评分为AI预估，不是官方IELTS成绩。"


class FeedbackEvaluationError(ValueError):
    """Raised when a provider cannot return valid writing feedback."""


def _extract_json(content: str) -> str:
    """Extract one JSON object from plain text or a fenced response."""

    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, count=1)
        cleaned = re.sub(r"\s*```$", "", cleaned, count=1)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise FeedbackEvaluationError("invalid_ai_json")
    return cleaned[start : end + 1]


def parse_feedback(content: str) -> WritingFeedbackSchema:
    """Parse provider JSON and enforce the standard V1 disclaimer."""

    try:
        data = json.loads(_extract_json(content))
        feedback = WritingFeedbackSchema.model_validate(data)
    except (
        json.JSONDecodeError,
        ValidationError,
        FeedbackEvaluationError,
    ) as error:
        raise FeedbackEvaluationError("invalid_ai_json") from error
    return feedback.model_copy(update={"disclaimer": WRITING_DISCLAIMER})


def build_writing_messages(essay: Essay) -> list[dict[str, str]]:
    """Build a bounded structured-feedback prompt for one essay."""

    schema_fields = ", ".join(WritingFeedbackSchema.model_fields)
    return [
        {
            "role": "system",
            "content": (
                "你是谨慎的IELTS写作学习反馈助手。按IELTS四项标准给出预估，"
                "不得声称是官方评分。只返回一个JSON对象，不要Markdown。"
                f"必须包含字段：{schema_fields}。分数为0到9的0.5分间隔；"
                "strengths、main_issues、actionable_suggestions均为字符串数组；"
                "rewrite_example只改写一个段落，不能代写整篇；"
                f"disclaimer必须为“{WRITING_DISCLAIMER}”"
            ),
        },
        {
            "role": "user",
            "content": (
                f"考试类型：{essay.test_type}\n任务：{essay.task_type}\n"
                f"题目：{essay.prompt}\n作文：\n{essay.content}"
            ),
        },
    ]


def request_valid_feedback(
    provider: AIProvider, essay: Essay
) -> tuple[WritingFeedbackSchema, str, str]:
    """Request valid structured feedback, retrying invalid JSON once."""

    messages = build_writing_messages(essay)
    try:
        first = provider.generate(messages, json_mode=True)
        try:
            return parse_feedback(first.content), first.provider, first.model_name
        except FeedbackEvaluationError:
            repair_messages = [
                *messages,
                {"role": "assistant", "content": first.content[:6000]},
                {
                    "role": "user",
                    "content": (
                        "上一个回复未通过结构校验。请严格按要求重新输出完整JSON，"
                        "不要添加解释或代码块。"
                    ),
                },
            ]
            second = provider.generate(repair_messages, json_mode=True)
            return (
                parse_feedback(second.content),
                second.provider,
                second.model_name,
            )
    except AIProviderError as error:
        raise FeedbackEvaluationError(error.code) from error
