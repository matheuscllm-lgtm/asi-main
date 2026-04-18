"""Tests for experiment single-run guard behavior."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


def _bootstrap_evolve_package() -> None:
    if "Evolve" in sys.modules:
        return

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "Evolve",
        root / "__init__.py",
        submodule_search_locations=[str(root)],
    )
    if spec is None or spec.loader is None:
        raise ImportError("Failed to bootstrap Evolve package for tests")

    module = importlib.util.module_from_spec(spec)
    sys.modules["Evolve"] = module
    spec.loader.exec_module(module)


_bootstrap_evolve_package()

from Evolve.pipeline.run_guard import ActiveRunError, RunGuard


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
