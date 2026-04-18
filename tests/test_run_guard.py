"""Tests for experiment single-run guard behavior."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import importlib.util

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "run_guard_test_module",
    _ROOT / "pipeline" / "run_guard.py",
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("Failed to load run_guard module")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
ActiveRunError = _MODULE.ActiveRunError
RunGuard = _MODULE.RunGuard


class RunGuardTests(unittest.TestCase):
    def test_second_acquire_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            exp_dir = Path(tmp_dir) / "exp"
            guard_1 = RunGuard(exp_dir)
            guard_2 = RunGuard(exp_dir)

            guard_1.acquire()
            try:
                with self.assertRaises(ActiveRunError):
                    guard_2.acquire()
            finally:
                guard_1.release()

    def test_stale_lock_recovered_when_pid_dead(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            exp_dir = Path(tmp_dir) / "exp"
            exp_dir.mkdir(parents=True, exist_ok=True)
            lock_file = exp_dir / ".active_run.lock"

            stale_payload = {
                "pid": 99999999,
                "started_at": "2026-04-18T00:00:00+00:00",
                "command": "old run",
                "host": "test-host",
            }
            lock_file.write_text(json.dumps(stale_payload), encoding="utf-8")

            guard = RunGuard(exp_dir)
            metadata = guard.acquire()
            try:
                self.assertIsInstance(metadata.get("pid"), int)
                stale_copy = exp_dir / ".active_run.stale.lock"
                self.assertTrue(stale_copy.exists())
                persisted = json.loads(stale_copy.read_text(encoding="utf-8"))
                self.assertEqual(persisted["pid"], stale_payload["pid"])
            finally:
                guard.release()


if __name__ == "__main__":
    unittest.main()
