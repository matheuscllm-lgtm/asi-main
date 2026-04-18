"""Atomic file persistence helpers used by manifest writers."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write text content atomically by replacing from a temp file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        "w",
        encoding=encoding,
        dir=str(target.parent),
        delete=False,
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)

    os.replace(tmp_path, target)


def atomic_write_json(path: Path, payload: Any, ensure_ascii: bool = False, indent: int = 2) -> None:
    """Serialize JSON and persist atomically."""
    content = json.dumps(payload, ensure_ascii=ensure_ascii, indent=indent)
    atomic_write_text(path=path, content=content)
