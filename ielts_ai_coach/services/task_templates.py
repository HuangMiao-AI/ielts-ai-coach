"""Deterministic, copyright-safe task templates for IELTS V1 plans."""

from __future__ import annotations

from ielts_ai_coach.services.question_bank import load_reading_catalog
from ielts_ai_coach.services.task_content import TaskContent


DIFFICULTY_LABELS = {
    "foundation": "基础",
    "targeted": "进阶",
    "exam": "冲刺",
}

WRITING_PROMPTS = (
    (
        "Academic",
        "Task 2",
        "Some people think schools should spend more time teaching practical "
        "life skills than traditional academic subjects. To what extent do "
        "you agree or disagree?",
    ),
    (
        "General",
        "Task 1",
        "You recently attended a short course at a local training centre. "
        "Write a letter to the manager. In your letter, describe the course, "
        "explain what you found useful, and suggest one improvement.",
    ),
)

def _listening_task(
    *,
    day_offset: int,
    planned_minutes: int,
    difficulty: str,
) -> TaskContent:
    """Build a material-selection listening task without copying test audio."""

    section = 3 if day_offset % 2 == 0 else 2
    question_type = "选择题与说话人匹配" if section == 3 else "表格填空"
    question_count = max(5, min(12, planned_minutes // 2))
    material = (
        f"请选择你合法拥有的 IELTS 听力材料：任一 Test 的 Section {section}。"
        "V1 不附带真题音频；请自行选择材料。"
    )
    return TaskContent(
        task_title=f"Section {section}：{question_type}精听复盘",
        objective=f"训练{question_type}的预判、定位和同义替换识别。",
        material=material,
        instructions=(
            f"先阅读并圈出前{question_count}题的关键词，预测答案类型。",
            f"播放音频并独立完成前{question_count}题，中途不查看答案。",
            "核对答案；错题回听对应句，记录原词与同义替换。",
            "最后再听一次错题片段，确认能听出答案依据。",
        ),
        completion_criteria=(
            f"完成{question_count}题、订正全部错题，并记录至少3组同义替换。"
        ),
        planned_minutes=planned_minutes,
        subject="listening",
        difficulty=difficulty,
        expected_output="答案记录、正确题数、错题定位句和3组同义替换。",
        template_id=f"L-V1-{section:03d}",
    )


def _reading_task(
    *,
    day_offset: int,
    planned_minutes: int,
    difficulty: str,
) -> TaskContent:
    """Build a task linked to one versioned original reading passage."""

    catalog = load_reading_catalog()
    passage = catalog[day_offset % len(catalog)]
    question_count = len(passage.questions)
    time_limit = max(12, min(25, planned_minutes - 5))
    return TaskContent(
        task_title=f"Academic Reading：{passage.title}",
        objective="完成一篇原创学术阅读，训练定位、改写识别和段落主旨匹配。",
        material=(
            f"IELTS AI Coach 项目原创阅读 {passage.passage_id}；"
            "非官方 IELTS 或 Cambridge 真题。"
        ),
        instructions=(
            f"点击“开始练习”，限时约{time_limit}分钟阅读全文。",
            f"独立完成{question_count}道题；提交前不会显示答案、解析或证据。",
            "确认所有问题均已作答后一次性提交。",
            "查看逐题结果、原文证据和错题原因，并保留历史记录。",
        ),
        completion_criteria=(
            f"完成全部{question_count}题并提交；"
            "系统自动评分并同步任务完成记录。"
        ),
        planned_minutes=planned_minutes,
        subject="reading",
        difficulty=difficulty,
        expected_output="总分、正确率、逐题判定、正确答案、解析与原文证据。",
        template_id=f"R-V2-{day_offset % len(catalog) + 1:03d}",
        reading_passage_id=passage.passage_id,
        reading_passage_version=passage.version,
    )


def _writing_task(
    *,
    day_offset: int,
    planned_minutes: int,
    difficulty: str,
) -> TaskContent:
    """Build an original writing prompt with a time-appropriate output."""

    test_type, task_type, prompt = WRITING_PROMPTS[day_offset % 2]
    full_target = 250 if task_type == "Task 2" else 150
    if planned_minutes >= 30:
        output = f"一篇不少于{full_target}词的完整作文和四项自查结果。"
        criteria = f"完成不少于{full_target}词，结构完整，并按四项标准自查。"
        title_action = "限时成文"
    else:
        output = "立场或写作目的、完整提纲，以及一个不少于80词的主体段。"
        criteria = "完成提纲和一个不少于80词的主体段，并标出主题句与例证。"
        title_action = "提纲与主体段"
    return TaskContent(
        task_title=f"{test_type} {task_type}：{title_action}",
        objective="提升任务回应、段落展开和论据与主题句的一致性。",
        material=f"IELTS AI Coach 原创题目：{prompt}",
        instructions=(
            "用2—3分钟圈出题目要求，确定立场或写作目的。",
            "列出段落提纲，每个主体段只保留一个中心观点。",
            f"按计划时间完成写作；完整练习的目标字数为{full_target}词。",
            "按任务回应、衔接、词汇和语法四项标准快速自查。",
        ),
        completion_criteria=criteria,
        planned_minutes=planned_minutes,
        subject="writing",
        difficulty=difficulty,
        expected_output=output,
        template_id=f"W-V1-{day_offset % 2 + 1:03d}",
        writing_test_type=test_type,
        writing_task_type=task_type,
        writing_prompt=prompt,
    )


def _speaking_task(
    *,
    day_offset: int,
    planned_minutes: int,
    difficulty: str,
) -> TaskContent:
    """Build a concrete self-recorded speaking practice task."""

    if day_offset % 2 == 0:
        title = "Part 2：一次有帮助的学习经历"
        questions = (
            "Describe a learning experience that was useful to you.",
            "You should say when it happened, what you learned, who helped you, "
            "and explain why it was useful.",
        )
        timing = "准备1分钟，连续回答1分30秒至2分钟"
    else:
        title = "Part 3：科技如何改变学习"
        questions = (
            "How has technology changed the way students learn?",
            "What are the disadvantages of depending on technology?",
            "Should schools teach students how to evaluate online information?",
        )
        timing = "每题准备20秒，回答40—60秒"
    return TaskContent(
        task_title=title,
        objective="训练持续表达、观点展开和自我纠错，减少无意义停顿。",
        material="IELTS AI Coach 原创口语题；使用手机自带录音工具即可。",
        instructions=(
            f"阅读题目并按要求计时：{timing}。",
            "第一次录音不中断，回答时使用“观点—原因—例子”结构。",
            "回听并记录一次长停顿、一次重复表达和一个语法问题。",
            "根据自评修改表达后再录一次；V1 不进行自动语音评分。",
        ),
        completion_criteria="完成2次录音，并写下3条具体自评和1个改进表达。",
        planned_minutes=planned_minutes,
        subject="speaking",
        difficulty=difficulty,
        expected_output="两次个人录音、3条自评和1个改进后的表达。",
        template_id=f"S-V1-{day_offset % 2 + 1:03d}",
        questions=questions,
    )


def build_task_content(
    *,
    subject: str,
    phase: str,
    day_offset: int,
    planned_minutes: int,
) -> TaskContent:
    """Return one executable task using only deterministic local rules."""

    difficulty = DIFFICULTY_LABELS.get(phase, "进阶")
    builders = {
        "listening": _listening_task,
        "reading": _reading_task,
        "writing": _writing_task,
        "speaking": _speaking_task,
    }
    if subject not in builders:
        raise ValueError("invalid_subject")
    return builders[subject](
        day_offset=day_offset,
        planned_minutes=planned_minutes,
        difficulty=difficulty,
    )
