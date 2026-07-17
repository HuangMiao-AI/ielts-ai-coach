"""Deterministic local AI provider used without an API key."""

from __future__ import annotations

import json

from ielts_ai_coach.ai.base import AIProvider, AIResponse


class MockAIProvider(AIProvider):
    """Return predictable local responses without network access."""

    @property
    def provider_name(self) -> str:
        """Return the provider identifier."""

        return "mock"

    @property
    def model_name(self) -> str:
        """Return the local model label."""

        return "mock-ielts-coach-v1"

    @property
    def is_mock(self) -> bool:
        """Return true for demonstration mode."""

        return True

    def _writing_response(self) -> str:
        """Return one valid structured writing-feedback example."""

        return json.dumps(
            {
                "task_response_or_achievement": 6.0,
                "coherence_and_cohesion": 6.0,
                "lexical_resource": 6.0,
                "grammatical_range_and_accuracy": 5.5,
                "estimated_overall": 6.0,
                "strengths": [
                    "文章能够表达主要观点，并使用了基本段落结构。"
                ],
                "main_issues": [
                    "部分论点展开不足，复杂句中的语法准确性需要提高。"
                ],
                "actionable_suggestions": [
                    "每个主体段增加一个具体例子，并解释它与观点的关系。",
                    "检查主谓一致、冠词和长句中的标点。",
                ],
                "rewrite_example": (
                    "例如，可将一个主体段改为：This change can benefit "
                    "students because it gives them more time to review "
                    "difficult concepts and apply them in practical tasks."
                ),
                "disclaimer": "该评分为AI预估，不是官方IELTS成绩。",
            },
            ensure_ascii=False,
        )

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
    ) -> AIResponse:
        """Generate a deterministic demonstration response."""

        if json_mode:
            content = self._writing_response()
        else:
            question = next(
                (
                    message["content"]
                    for message in reversed(messages)
                    if message.get("role") == "user"
                ),
                "你的雅思学习问题",
            )
            content = (
                f"演示建议：针对“{question[:80]}”，先完成今天计划中的最高"
                "优先级任务，再用10分钟记录错误原因。结合你的弱项，建议把"
                "练习分成“方法复习—限时训练—错题复盘”三个步骤。"
                "\n\n以上建议仅供学习参考，不替代正式教师指导或官方评分。"
            )
        return AIResponse(
            content=content,
            provider=self.provider_name,
            model_name=self.model_name,
        )
