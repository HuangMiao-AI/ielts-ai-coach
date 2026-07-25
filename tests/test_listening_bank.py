"""Validation contracts for the original offline Listening bank."""

from __future__ import annotations

from pathlib import Path
import wave

from ielts_ai_coach.services.listening_bank import load_listening_bank


PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUESTION_TYPES = {
    "multiple_choice",
    "form_completion",
    "note_completion",
}


def test_listening_bank_has_two_original_complete_tests() -> None:
    """The bundled release has the approved shape and copyright metadata."""

    bank = load_listening_bank()

    assert bank.version == "1.0"
    assert bank.source_type == "project_original"
    assert bank.is_official_ielts_content is False
    assert "非官方 IELTS 或 Cambridge" in bank.copyright_notice
    assert len(bank.tests) == 2
    assert len({test.test_id for test in bank.tests}) == 2
    question_ids: list[str] = []
    for test in bank.tests:
        assert len(test.sections) == 2
        questions = test.questions
        assert len(questions) == 16
        assert {question.question_type for question in questions} == QUESTION_TYPES
        assert all(question.explanation for question in questions)
        assert all(question.evidence for question in questions)
        assert all(section.script for section in test.sections)
        assert all(
            turn.speaker in {"Speaker A", "Speaker B", "Narrator"}
            for section in test.sections
            for turn in section.script
        )
        question_ids.extend(question.question_id for question in questions)
    assert len(question_ids) == len(set(question_ids)) == 32


def test_listening_audio_assets_are_valid_audible_wav_files() -> None:
    """Each test references committed PCM audio with a positive duration."""

    for test in load_listening_bank().tests:
        audio_path = PROJECT_ROOT / test.audio_path
        assert audio_path.read_bytes()[:4] == b"RIFF"
        with wave.open(str(audio_path), "rb") as audio:
            assert audio.getnchannels() >= 1
            assert audio.getframerate() > 0
            assert audio.getnframes() > audio.getframerate()
            frames = audio.readframes(audio.getnframes())
            assert any(byte != 0 for byte in frames)
