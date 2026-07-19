"""Same-directory atomic UTF-8 file writes."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile

from ielts_ai_coach.exporting.errors import ExportWriteError


def atomic_write_text(target: Path, content: str) -> None:
    """Write text through a flushed temporary file and atomic replacement."""

    temporary_path: Path | None = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, target)
        temporary_path = None
    except (OSError, UnicodeError) as exc:
        raise ExportWriteError("atomic_write_failed") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
