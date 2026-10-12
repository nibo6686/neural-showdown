"""Run only the local saved-HTML candidate's bounded validation gates."""
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/planning"
PYTHON = r"D:\Anaconda\envs\neuralgpu\python.exe"
ENV = dict(os.environ, PYTHON=PYTHON, PYTHONPATH=str(ROOT / "trainer/src"))
for key in ("PYTHONUTF8", "PYTHONIOENCODING", "PERSPECTIVE_REPLAY_REQUIREMENTS", "PERSPECTIVE_REPLAY_REPORT", "LOCAL_REPLAY_HTML_REPORT"):
    ENV.pop(key, None)
runs = []


def run(label, command, *, extra=None, expected_exit=0, cwd=ROOT):
    env = dict(ENV, **(extra or {}))
    start = time.monotonic()
    child = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=60)
    text = (child.stdout + child.stderr).decode("utf-8", errors="replace")
    (OUT / f"perspective-fidelity-prompt18-{label}.log").write_bytes(("\n".join(line.rstrip() for line in text.splitlines()) + "\n").encode("utf-8"))
    runs.append({"label": label, "argv": command, "cwd": str(cwd), "encoding_overrides": "both unset", "PYTHON": PYTHON, "PYTHONPATH": ENV["PYTHONPATH"], "extra_environment": extra or {}, "exit_code": child.returncode, "expected_exit": expected_exit, "seconds": round(time.monotonic()-start, 3), "counts": re.findall(r'(?:Ran \d+ tests|tests \d+|pass \d+|fail \d+|FAILED \(failures=\d+\)|^OK$)', text, re.M)})
    (OUT / "perspective-fidelity-prompt18-validation.json").write_text(json.dumps(runs, indent=2)+"\n", encoding="utf-8")
    print(label, child.returncode, runs[-1]["counts"], flush=True)
    assert child.returncode == expected_exit, text[-5000:]


run("import-resolution", [PYTHON, "-c", "from pathlib import Path; import neural.compare_action_rankers as m; assert Path(m.__file__).resolve() == Path('trainer/src/neural/compare_action_rankers.py').resolve()"])
run("loader", [PYTHON, "-m", "unittest", "trainer.tests.test_local_replay_html_transport", "-v"], extra={"LOCAL_REPLAY_HTML_REPORT": str(OUT / "perspective-fidelity-prompt18-after-probe.json")})
run("transport-requirement", [PYTHON, "-m", "unittest", "trainer.tests.test_local_replay_html_transport.LocalReplayHTMLTransportTest.test_supplied_fixtures_literal_hp_and_index_mapping", "-v"])
run("python-characterization", [PYTHON, "-m", "unittest", "trainer.tests.test_perspective_replay_characterization", "-v"], extra={"PERSPECTIVE_REPLAY_REPORT": str(OUT / "perspective-fidelity-prompt18-python-characterization.json")})
run("python-requirements", [PYTHON, "-m", "unittest", "trainer.tests.test_perspective_replay_characterization", "-v"], extra={"PERSPECTIVE_REPLAY_REQUIREMENTS": "1", "PERSPECTIVE_REPLAY_REPORT": str(OUT / "perspective-fidelity-prompt18-python-requirements.json")}, expected_exit=1)
parser = "trainer.tests.test_public_replays.PublicReplayParserTest."
run("existing-parser", [PYTHON, "-m", "unittest", "-v"] + [parser+n for n in ("test_protocol_log_parser_extracts_battle_events", "test_disconnect_line_followed_by_win_preserves_winner", "test_inactive_timer_line_followed_by_win_preserves_winner")])
sources = list((ROOT / "sim-core/src").rglob("*.ts")) + [ROOT / "sim-core/tests/perspective_replay_characterization.test.ts"]
stale = []
for source in sources:
    compiled = ROOT / "sim-core/dist" / source.relative_to(ROOT / "sim-core").with_suffix(".js")
    if not compiled.exists() or source.stat().st_mtime_ns > compiled.stat().st_mtime_ns:
        stale.append(str(source.relative_to(ROOT)))
(OUT / "perspective-fidelity-prompt18-ts-freshness.json").write_text(json.dumps({"checked_inputs": len(sources), "stale": stale, "build_required": bool(stale), "TS_sources_changed": False}, indent=2)+"\n", encoding="utf-8")
if stale:
    run("required-stale-build", ["node", "node_modules/typescript/bin/tsc", "-p", "tsconfig.json"], cwd=ROOT / "sim-core")
run("ts-characterization", ["node", "--test", "--test-isolation=none", "sim-core/dist/tests/perspective_replay_characterization.test.js"])
run("ts-requirements", ["node", "--test", "--test-isolation=none", "sim-core/dist/tests/perspective_replay_characterization.test.js"], extra={"PERSPECTIVE_REPLAY_REQUIREMENTS": "1"}, expected_exit=1)
run("diff-check", ["git", "diff", "--check"])
