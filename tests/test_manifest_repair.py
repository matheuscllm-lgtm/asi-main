"""Tests for canonical manifest repair helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import types
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]

if "Evolve" not in sys.modules:
    evolve_pkg = types.ModuleType("Evolve")
    evolve_pkg.__path__ = [str(_ROOT)]
    sys.modules["Evolve"] = evolve_pkg

if "Evolve.utils" not in sys.modules:
    utils_pkg = types.ModuleType("Evolve.utils")
    utils_pkg.__path__ = [str(_ROOT / "utils")]
    sys.modules["Evolve.utils"] = utils_pkg

structures_spec = importlib.util.spec_from_file_location(
    "Evolve.utils.structures",
    _ROOT / "utils" / "structures.py",
)
if structures_spec is None or structures_spec.loader is None:
    raise ImportError("Failed to load structures module")
structures_module = importlib.util.module_from_spec(structures_spec)
sys.modules["Evolve.utils.structures"] = structures_module
structures_spec.loader.exec_module(structures_module)

best_snapshot_spec = importlib.util.spec_from_file_location(
    "Evolve.utils.best_snapshot",
    _ROOT / "utils" / "best_snapshot.py",
)
if best_snapshot_spec is None or best_snapshot_spec.loader is None:
    raise ImportError("Failed to load best_snapshot module")
best_snapshot_module = importlib.util.module_from_spec(best_snapshot_spec)
sys.modules["Evolve.utils.best_snapshot"] = best_snapshot_module
best_snapshot_spec.loader.exec_module(best_snapshot_module)

BestSnapshotManager = best_snapshot_module.BestSnapshotManager
Node = structures_module.Node


class ManifestRepairTests(unittest.TestCase):
    def test_best_snapshot_repair_overwrites_noncanonical_best(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            steps_dir = Path(tmp_dir) / "steps"
            old_best_dir = steps_dir / "best" / "step_99"
            old_best_dir.mkdir(parents=True, exist_ok=True)
            (old_best_dir / "results.json").write_text('{"score": 9.9}', encoding="utf-8")

            manager = BestSnapshotManager(steps_dir)
            nodes = [
                Node(id=1, name="node_1", score=0.70, results={"score": 0.70}),
                Node(
                    id=2,
                    name="node_2",
                    score=0.76,
                    results={"score": 0.76},
                    meta_info={"step_name": "step_2"},
                ),
            ]

            rebuilt = manager.repair_from_nodes(nodes)

            self.assertEqual(rebuilt, "step_2")
            self.assertFalse((steps_dir / "best" / "step_99").exists())
            rebuilt_results = json.loads(
                (steps_dir / "best" / "step_2" / "results.json").read_text(encoding="utf-8")
            )
            self.assertEqual(rebuilt_results["score"], 0.76)


if __name__ == "__main__":
    unittest.main()
