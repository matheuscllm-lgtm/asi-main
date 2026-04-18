"""Single-active-run guard for experiment directories."""

from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class RunGuardError(RuntimeError):
    """Base run guard exception."""


class ActiveRunError(RunGuardError):
    """Raised when an active lock is present for the target experiment."""


class RunGuard:
    """File-based guard that allows only one active process per experiment."""

    def __init__(self, experiment_dir: Path, lock_filename: str = ".active_run.lock") -> None:
        self.experiment_dir = Path(experiment_dir)
        self.lock_file = self.experiment_dir / lock_filename
        self._acquired = False
        self._metadata: Dict[str, Any] = {}

    def acquire(self) -> Dict[str, Any]:
        """Acquire lock in non-blocking mode or raise ``ActiveRunError``."""
        if self._acquired:
            return self._metadata

        self.experiment_dir.mkdir(parents=True, exist_ok=True)

        existing = self._read_lock()
        if existing is not None:
            self._handle_existing_lock(existing)

        metadata = self._build_metadata()
        try:
            fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            existing = self._read_lock() or {}
            raise ActiveRunError(self._format_active_message(existing)) from None

        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())

        self._acquired = True
        self._metadata = metadata
        return metadata

    def release(self) -> None:
        """Release lock owned by this process."""
        if not self._acquired:
            return

        lock_data = self._read_lock()
        if lock_data is None:
            self._acquired = False
            self._metadata = {}
            return

        if self._is_our_lock(lock_data):
            self.lock_file.unlink(missing_ok=True)

        self._acquired = False
        self._metadata = {}

    def _build_metadata(self) -> Dict[str, Any]:
        return {
            "pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "command": " ".join(sys.argv),
            "host": socket.gethostname(),
        }

    def _read_lock(self) -> Dict[str, Any] | None:
        if not self.lock_file.exists():
            return None
        try:
            return json.loads(self.lock_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _handle_existing_lock(self, lock_data: Dict[str, Any]) -> None:
        pid = lock_data.get("pid")
        if not isinstance(pid, int):
            raise ActiveRunError(
                "Existing run lock is missing a valid pid; refusing stale recovery without process proof."
            )

        if self._pid_is_alive(pid):
            raise ActiveRunError(self._format_active_message(lock_data))

        # Stale lock: process is provably dead.
        backup_path = self.lock_file.with_suffix(".stale.lock")
        self._atomic_write_json(backup_path, lock_data)
        self.lock_file.unlink(missing_ok=True)

    def _is_our_lock(self, lock_data: Dict[str, Any]) -> bool:
        return (
            lock_data.get("pid") == self._metadata.get("pid")
            and lock_data.get("started_at") == self._metadata.get("started_at")
        )

    def _pid_is_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _format_active_message(self, lock_data: Dict[str, Any]) -> str:
        pid = lock_data.get("pid", "unknown")
        started_at = lock_data.get("started_at", "unknown")
        command = lock_data.get("command", "unknown")
        host = lock_data.get("host", "unknown")
        return (
            "Another active run is already holding the experiment lock: "
            f"pid={pid}, host={host}, started_at={started_at}, command={command}"
        )

    def _atomic_write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(target.parent),
            delete=False,
        ) as tmp:
            json.dump(payload, tmp, ensure_ascii=False, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, target)
