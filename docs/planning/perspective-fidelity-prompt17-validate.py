"""Bounded local evidence runner; no production writes, installs, fetching or publication."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
PYTHON = r"D:\Anaconda\envs\neuralgpu\python.exe"
OUT = ROOT / "docs/planning"
env = dict(os.environ, PYTHON=PYTHON, PYTHONPATH=str(ROOT / "trainer/src"))
for key in ("PYTHONUTF8", "PYTHONIOENCODING", "PERSPECTIVE_REPLAY_REQUIREMENTS", "PERSPECTIVE_REPLAY_REPORT"):
    env.pop(key, None)
runs = []


def run(label, command, *, cwd=ROOT, requirements=False, matrix=None, expected_exit=0):
    child_env = dict(env)
    if requirements:
        child_env["PERSPECTIVE_REPLAY_REQUIREMENTS"] = "1"
    if matrix:
        child_env["PERSPECTIVE_REPLAY_REPORT"] = str(OUT / f"perspective-fidelity-prompt17-{matrix}.json")
    start = time.monotonic()
    child = subprocess.run(command, cwd=cwd, env=child_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
    output = child.stdout.decode("utf-8", errors="replace")
    log = OUT / f"perspective-fidelity-prompt17-{label}.log"
    # Store readable output once; avoid Windows doubling child CRLF on write.
    log.write_bytes(("\n".join(line.rstrip() for line in output.splitlines()) + "\n").encode("utf-8"))
    result = {"label": label, "cwd": str(cwd), "argv": command, "encoding_overrides": "unset", "PYTHON": PYTHON, "PYTHONPATH": child_env["PYTHONPATH"], "requirements": requirements, "matrix": matrix, "exit_code": child.returncode, "expected_exit": expected_exit, "seconds": round(time.monotonic()-start, 3), "log": log.name}
    runs.append(result)
    (OUT / "perspective-fidelity-prompt17-validation.json").write_text(json.dumps(runs, indent=2) + "\n", encoding="utf-8")
    print(label, child.returncode, result["seconds"], flush=True)
    assert child.returncode == expected_exit, output[-5000:]


run("build", ["node", "node_modules/typescript/bin/tsc", "-p", "tsconfig.json"], cwd=ROOT/"sim-core")
py = [PYTHON, "-m", "unittest", "trainer.tests.test_perspective_replay_characterization", "-v"]
ts = ["node", "--test", "--test-isolation=none", "sim-core/dist/tests/perspective_replay_characterization.test.js"]
run("python-requirements-final", py, requirements=True, matrix="python-requirements-final", expected_exit=1)
run("ts-requirements-final", ts, requirements=True, matrix="ts-requirements-final", expected_exit=1)
run("python-characterization", py, matrix="python-characterization")
run("ts-characterization", ts, matrix="ts-characterization")
parser = "trainer.tests.test_public_replays.PublicReplayParserTest."
run("existing-parser", [PYTHON, "-m", "unittest", "-v"] + [parser+n for n in ["test_protocol_log_parser_extracts_battle_events", "test_disconnect_line_followed_by_win_preserves_winner", "test_inactive_timer_line_followed_by_win_preserves_winner"]])
reconstruction = "trainer.tests.test_benchmark_vnext_featuregen.VNextFeaturegenBenchmarkTest."
run("existing-reconstruction", [PYTHON, "-m", "unittest", "-v"] + [reconstruction+n for n in ["test_completed_team_assigns_moves_to_active_species_not_actor_alias", "test_public_illusion_replace_updates_active_identity", "test_public_illusion_replace_restores_true_bench_switch", "test_ditto_transform_exposes_current_stint_copied_move", "test_ditto_transform_excludes_future_transform_stint_move", "test_transform_copied_moves_not_globally_backfilled_into_species"]])
run("existing-extractor", ["node", "--test", "--test-isolation=none", "sim-core/dist/tests/state_extractor.test.js"])
run("diff-check", ["git", "diff", "--check"])
