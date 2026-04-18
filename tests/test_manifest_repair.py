"""Tests for canonical manifest repair helpers."""

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

from Evolve.pipeline.manifest_repair import canonical_step_from_nodes
from Evolve.utils.best_snapshot import BestSnapshotManager
from Evolve.utils.structures import Node


class ManifestRepairTests(unittest.TestCase):
    def test_canonical_step_uses_max_node_id_plus_one_without_initial(self) -> None:
        step = canonical_step_from_nodes(
            [
                Node(id=0, name="node_0", score=0.10),
                Node(id=1, name="node_1", score=0.20),
                Node(id=2, name="node_2", score=0.30),
            ]
        )
        self.assertEqual(step, 3)

    def test_canonical_step_preserves_initial_program_baseline(self) -> None:
        step = canonical_step_from_nodes([Node(id=0, name="initial_program", score=0.76)])
        self.assertEqual(step, 0)

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
