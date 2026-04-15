from __future__ import annotations

import json
import shutil
import subprocess
import sys
import textwrap
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = REPO_ROOT / "skills" / "evolve" / "scripts"
LOCAL_TEMP_ROOT = REPO_ROOT / ".test_tmp"
LOCAL_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def run_cli(script_name: str, *args: str, cwd: Path = REPO_ROOT, check: bool = True):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_ROOT / script_name), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"{script_name} failed with code {completed.returncode}\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return completed


def run_cli_json(script_name: str, *args: str, cwd: Path = REPO_ROOT, check: bool = True):
    completed = run_cli(script_name, *args, cwd=cwd, check=check)
    payload = json.loads(completed.stdout or "{}")
    return completed, payload


def normalize_confirmed_run(workspace_root: Path, run_name: str) -> Path:
    _, payload = run_cli_json(
        "evolve-brief",
        "normalize",
        "--workspace-root",
        str(workspace_root),
        "--run-name",
        run_name,
        "--objective",
        "maximize benchmark score",
        "--core-score",
        "score",
        "--evaluation-command",
        "python -c \"import json; json.dump({'success': True, 'eval_score': 1.0, 'score': 1.0}, open({quoted_results_path}, 'w'))\"",
        "--success-criterion",
        "maximize score",
        "--max-rounds",
        "3",
        "--patience",
        "1",
        "--stop-condition",
        "budget_exhausted",
        "--writable-path",
        "allowed",
        "--primary-target",
        "allowed/program.py",
        "--sampling-algorithm",
        "ucb1",
        "--sample-n",
        "2",
        "--cognition-source-mode",
        "user",
        "--confirmed",
        "true",
        cwd=REPO_ROOT,
    )
    return Path(payload["run_dir"])


@contextmanager
def temporary_workspace():
    workspace = LOCAL_TEMP_ROOT / f"ws_{uuid4().hex}"
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        yield workspace
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


class EvolveSkillTests(unittest.TestCase):
    def test_preflight_missing_info_blocks_evolve(self):
        with temporary_workspace() as workspace:
            _, payload = run_cli_json(
                "evolve-brief",
                "normalize",
                "--workspace-root",
                str(workspace),
                "--run-name",
                "draft-run",
                "--objective",
                "optimize something",
            )
            run_dir = payload["run_dir"]

            completed = run_cli(
                "evolve-db",
                "sample",
                "--run-dir",
                run_dir,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("Preflight is incomplete", completed.stderr)

    def test_brief_normalize_supports_existing_eval_and_verbal_paths(self):
        with temporary_workspace() as workspace:
            eval_script = workspace / "eval.py"
            eval_script.write_text("print('ok')\n", encoding="utf-8")

            _, scripted = run_cli_json(
                "evolve-brief",
                "normalize",
                "--workspace-root",
                str(workspace),
                "--run-name",
                "scripted",
                "--objective",
                "score scripted evaluator",
                "--core-score",
                "score",
                "--evaluation-command",
                "python {quoted_script_path}",
                "--evaluation-script-path",
                str(eval_script),
                "--success-criterion",
                "maximize score",
                "--max-rounds",
                "3",
                "--patience",
                "1",
                "--stop-condition",
                "budget_exhausted",
                "--writable-path",
                ".",
                "--primary-target",
                "target.py",
                "--sampling-algorithm",
                "ucb1",
                "--sample-n",
                "2",
                "--cognition-source-mode",
                "user",
            )
            scripted_spec = yaml.safe_load(
                Path(scripted["run_spec"]).read_text(encoding="utf-8")
            )
            self.assertEqual(scripted_spec["evaluation"]["script_path"], "eval.py")

            _, verbal = run_cli_json(
                "evolve-brief",
                "normalize",
                "--workspace-root",
                str(workspace),
                "--run-name",
                "verbal",
                "--objective",
                "score verbal evaluator later",
                "--core-score",
                "score",
                "--max-rounds",
                "2",
                "--patience",
                "0",
                "--stop-condition",
                "need_eval_definition",
                "--writable-path",
                ".",
                "--primary-target",
                "candidate.py",
                "--sampling-algorithm",
                "ucb1",
                "--sample-n",
                "1",
                "--cognition-source-mode",
                "user",
            )
            verbal_spec = yaml.safe_load(
                Path(verbal["run_spec"]).read_text(encoding="utf-8")
            )
            self.assertIn("evaluation", verbal_spec)
            self.assertEqual(verbal_spec["approval"]["confirmed"], False)
            self.assertIn("evaluation.command_or_script", verbal["missing_fields"])

            _, inspected = run_cli_json(
                "evolve-eval",
                "inspect",
                "--script-path",
                str(eval_script),
            )
            self.assertTrue(inspected["exists"])
            self.assertIn("print('ok')", inspected["preview"])

    def test_cognition_init_supports_user_and_candidate_sources(self):
        with temporary_workspace() as workspace:
            run_dir = build_run_dir_for_test(workspace, "cognition-run")
            seed_path = run_dir / "cognition_seed.md"
            seed_path.parent.mkdir(parents=True, exist_ok=True)
            seed_path.write_text(
                textwrap.dedent(
                    """
                    # Cognition

                    ```json
                    [
                      {
                        "content": "Use user supplied heuristics first.",
                        "source": "user",
                        "metadata": {"origin": "user"}
                      },
                      {
                        "content": "Subagent candidate: try a more diverse search.",
                        "source": "subagent",
                        "metadata": {"origin": "subagent"}
                      }
                    ]
                    ```
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            _, init_payload = run_cli_json(
                "evolve-cognition",
                "init",
                "--run-dir",
                str(run_dir),
                "--seed-file",
                str(seed_path),
                "--reset",
            )
            self.assertEqual(init_payload["items_added"], 2)

            _, add_payload = run_cli_json(
                "evolve-cognition",
                "add",
                "--run-dir",
                str(run_dir),
                "--item",
                "Extra manual heuristic",
                "--source",
                "user",
                "--kind",
                "note",
            )
            self.assertEqual(add_payload["items_added"], 1)

            _, search_payload = run_cli_json(
                "evolve-cognition",
                "search",
                "--run-dir",
                str(run_dir),
                "--query",
                "Subagent candidate: try a more diverse search.",
                "--top-k",
                "3",
            )
            self.assertGreaterEqual(len(search_payload["matches"]), 1)

    def test_approval_false_rejects_evolve_commands(self):
        with temporary_workspace() as workspace:
            _, payload = run_cli_json(
                "evolve-brief",
                "normalize",
                "--workspace-root",
                str(workspace),
                "--run-name",
                "awaiting-approval",
                "--objective",
                "maximize score",
                "--core-score",
                "score",
                "--evaluation-command",
                "python -c \"print('noop')\"",
                "--success-criterion",
                "maximize score",
                "--max-rounds",
                "2",
                "--patience",
                "0",
                "--stop-condition",
                "budget_exhausted",
                "--writable-path",
                ".",
                "--primary-target",
                "candidate.py",
                "--sampling-algorithm",
                "ucb1",
                "--sample-n",
                "1",
                "--cognition-source-mode",
                "user",
                "--confirmed",
                "false",
            )

            completed = run_cli(
                "evolve-eval",
                "run",
                "--run-dir",
                payload["run_dir"],
                "--code-path",
                "candidate.py",
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("Preflight is not confirmed yet", completed.stderr)

    def test_db_record_sample_best_and_stats_cover_algorithms(self):
        with temporary_workspace() as workspace:
            allowed = workspace / "allowed"
            allowed.mkdir(parents=True, exist_ok=True)
            run_dir = normalize_confirmed_run(workspace, "db-run")

            for index, score in enumerate([1.0, 2.0, 3.0], start=1):
                code_path = allowed / f"prog_{index}.py"
                code_path.write_text(f"print({index})\n", encoding="utf-8")
                results_path = allowed / f"results_{index}.json"
                results_path.write_text(
                    json.dumps({"score": score, "eval_score": score, "success": True}),
                    encoding="utf-8",
                )
                run_cli_json(
                    "evolve-db",
                    "record",
                    "--run-dir",
                    str(run_dir),
                    "--step-name",
                    f"step_{index}",
                    "--name",
                    f"node_{index}",
                    "--code-path",
                    str(code_path),
                    "--results-file",
                    str(results_path),
                    "--analysis",
                    f"analysis {index}",
                    "--motivation",
                    f"motivation {index}",
                    "--score",
                    str(score),
                )

            for algorithm in ["ucb1", "greedy", "random", "island"]:
                _, sample_payload = run_cli_json(
                    "evolve-db",
                    "sample",
                    "--run-dir",
                    str(run_dir),
                    "--algorithm",
                    algorithm,
                    "--n",
                    "2",
                )
                self.assertLessEqual(len(sample_payload["nodes"]), 2)

            _, best_payload = run_cli_json(
                "evolve-db",
                "best",
                "--run-dir",
                str(run_dir),
            )
            self.assertEqual(best_payload["best"]["name"], "node_3")

            _, stats_payload = run_cli_json(
                "evolve-db",
                "stats",
                "--run-dir",
                str(run_dir),
            )
            self.assertEqual(stats_payload["total_nodes"], 3)

    def test_evolve_files_enforces_writable_scope(self):
        with temporary_workspace() as workspace:
            allowed = workspace / "allowed"
            blocked = workspace / "blocked"
            allowed.mkdir(parents=True, exist_ok=True)
            blocked.mkdir(parents=True, exist_ok=True)
            run_dir = normalize_confirmed_run(workspace, "file-run")

            _, write_payload = run_cli_json(
                "evolve-files",
                "write",
                "--run-dir",
                str(run_dir),
                "--path",
                str(allowed / "program.py"),
                "--content",
                "print('ok')\n",
            )
            self.assertTrue(Path(write_payload["path"]).exists())

            _, read_payload = run_cli_json(
                "evolve-files",
                "read",
                "--run-dir",
                str(run_dir),
                "--path",
                str(allowed / "program.py"),
            )
            self.assertIn("print('ok')", read_payload["content"])

            blocked_result = run_cli(
                "evolve-files",
                "write",
                "--run-dir",
                str(run_dir),
                "--path",
                str(blocked / "secret.py"),
                "--content",
                "print('nope')\n",
                check=False,
            )
            self.assertNotEqual(blocked_result.returncode, 0)
            self.assertIn("outside the approved mutation scope", blocked_result.stderr)

    def test_circle_packing_acceptance_flow(self):
        run_name = "test-circle-packing-skill"
        run_dir = REPO_ROOT / ".evolve_runs" / run_name
        if run_dir.exists():
            shutil.rmtree(run_dir)

        try:
            evaluator = REPO_ROOT / "experiments" / "circle_packing_demo" / "evaluator.py"
            initial_program = REPO_ROOT / "experiments" / "circle_packing_demo" / "initial_program"

            _, payload = run_cli_json(
                "evolve-brief",
                "normalize",
                "--workspace-root",
                str(REPO_ROOT),
                "--run-name",
                run_name,
                "--objective",
                "maximize valid circle packing score",
                "--core-score",
                "combined_score",
                "--secondary-metric",
                "sum_radii",
                "--secondary-metric",
                "validity",
                "--evaluation-command",
                "python {quoted_script_path} {quoted_code_path} {quoted_results_path}",
                "--evaluation-script-path",
                str(evaluator),
                "--success-criterion",
                "maximize combined_score",
                "--success-criterion",
                "preserve valid packing",
                "--max-rounds",
                "1",
                "--patience",
                "0",
                "--stop-condition",
                "budget_exhausted",
                "--writable-path",
                "experiments/circle_packing_demo",
                "--primary-target",
                "experiments/circle_packing_demo/initial_program",
                "--sampling-algorithm",
                "island",
                "--sample-n",
                "1",
                "--cognition-source-mode",
                "mixed",
                "--seed-note",
                "Seed with circle packing geometry heuristics.",
            )
            run_dir = Path(payload["run_dir"])

            seed_file = run_dir / "cognition_seed.md"
            seed_file.write_text(
                textwrap.dedent(
                    """
                    # Circle Packing Seeds

                    ```json
                    [
                      {
                        "content": "Favor valid packings and preserve boundary checks.",
                        "source": "user",
                        "metadata": {"kind": "constraint"}
                      },
                      {
                        "content": "Variable radii and incremental geometry tweaks are useful search directions.",
                        "source": "subagent",
                        "metadata": {"kind": "candidate"}
                      }
                    ]
                    ```
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            run_cli_json(
                "evolve-cognition",
                "init",
                "--run-dir",
                str(run_dir),
                "--seed-file",
                str(seed_file),
                "--reset",
            )

            run_cli_json(
                "evolve-brief",
                "normalize",
                "--workspace-root",
                str(REPO_ROOT),
                "--run-name",
                run_name,
                "--confirmed",
                "true",
            )

            _, eval_payload = run_cli_json(
                "evolve-eval",
                "run",
                "--run-dir",
                str(run_dir),
                "--code-path",
                str(initial_program),
                "--step-name",
                "step_1",
            )
            results_path = Path(eval_payload["results_path"])
            self.assertTrue(results_path.exists())

            run_cli_json(
                "evolve-db",
                "record",
                "--run-dir",
                str(run_dir),
                "--step-name",
                "step_1",
                "--name",
                "initial_circle_packing",
                "--code-path",
                str(run_dir / "steps" / "step_1" / "code"),
                "--results-file",
                str(results_path),
                "--analysis",
                "Initial circle packing candidate recorded for evolve.",
                "--motivation",
                "Seed the run with the baseline constructor.",
            )

            _, sample_payload = run_cli_json(
                "evolve-db",
                "sample",
                "--run-dir",
                str(run_dir),
                "--n",
                "1",
            )
            self.assertEqual(len(sample_payload["nodes"]), 1)

            run_cli_json(
                "evolve-summary",
                "final",
                "--run-dir",
                str(run_dir),
            )

            self.assertTrue((run_dir / "preflight_summary.md").exists())
            self.assertTrue((run_dir / "steps" / "step_1" / "code").exists())
            self.assertTrue((run_dir / "steps" / "step_1" / "node.json").exists())
            self.assertTrue((run_dir / "best" / "step_1" / "code").exists())

            command_text = (run_dir / "steps" / "step_1" / "eval.command.txt").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("main.py", command_text)
            self.assertIn("evaluator.py", command_text)
        finally:
            if run_dir.exists():
                shutil.rmtree(run_dir)


def build_run_dir_for_test(workspace_root: Path, run_name: str) -> Path:
    return workspace_root / ".evolve_runs" / run_name


if __name__ == "__main__":
    unittest.main()
