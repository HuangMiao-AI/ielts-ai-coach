"""Tests for Python compatibility and source quality limits."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ielts_ai_coach.config import ensure_supported_python


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_python_312_is_required() -> None:
    """The application must accept 3.12 and reject other minor versions."""

    ensure_supported_python((3, 12))
    with pytest.raises(RuntimeError):
        ensure_supported_python((3, 13))


def test_v1_python_files_are_small_and_documented() -> None:
    """New Python modules should stay under 300 lines with function docstrings."""

    python_files = [PROJECT_ROOT / "app.py"]
    python_files.extend(
        (PROJECT_ROOT / "ielts_ai_coach").rglob("*.py")
    )

    for python_file in python_files:
        source = python_file.read_text(encoding="utf-8")
        assert len(source.splitlines()) < 300, python_file
        tree = ast.parse(source)
        functions = (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        for function in functions:
            assert ast.get_docstring(function), (
                f"{python_file}:{function.lineno} is missing a docstring"
            )
