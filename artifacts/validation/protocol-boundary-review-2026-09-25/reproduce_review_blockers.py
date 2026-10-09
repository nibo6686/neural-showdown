"""Reproduce the blocked protocol-contract review findings on macOS.

Run after ``cd`` to the repository root and a TypeScript build:
PYTHONPATH=trainer/src:trainer/tests python3 \
  artifacts/validation/protocol-boundary-review-2026-09-25/reproduce_review_blockers.py
"""
import itertools
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
os.chdir(ROOT)
sys.path[:0] = [str(ROOT / "trainer/src"), str(ROOT / "trainer/tests")]

from test_pipeline_record import _bundle, _rehashed_protocol_candidate
from neural.pipeline_record import main, validate_pipeline_bundle
from neural.protocol_contract import ProtocolRecordError, validate_protocol_record
from neural.ts_identity import verify_bundle_identities


TS_PROBE = r"""
const fs = require('node:fs');
const { validateRawProtocolRecord } = require(process.argv[1]);
const { projectPipelineProtocolPrefix } = require(process.argv[2]);
const records = JSON.parse(fs.readFileSync(0, 'utf8'));
const accepted = records.map(record => {
  try { validateRawProtocolRecord(record); return true; }
  catch { return false; }
});
console.log(JSON.stringify({
  accepted,
  projectedMalformedRequest: projectPipelineProtocolPrefix(['|request|not-json']),
  projectedTier: projectPipelineProtocolPrefix(['|tier|']),
}));
"""


def typescript_probe(records):
    result = subprocess.run(
        [
            "node", "-e", TS_PROBE,
            str(ROOT / "sim-core/dist/src/observable_state.js"),
            str(ROOT / "sim-core/dist/src/pipeline_integration.js"),
        ],
        cwd=ROOT,
        input=json.dumps(records),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def loader_asset_probes():
    malformed_schema = {
        "schema_version": "showdown-protocol-contract/v1",
        "supported_commands": "move",
        "recognized_unsupported_commands": [],
        "record_fixtures": [],
        "rejection_fixtures": [],
        "disposition_rules": [],
    }
    outcomes = {}
    for name, asset in (("missing", None), ("invalid_json", "{"), ("wrong_shape", json.dumps(malformed_schema))):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temp_dir:
            sandbox = Path(temp_dir)
            python_package = sandbox / "python/neural"
            python_package.mkdir(parents=True)
            (python_package / "__init__.py").write_text("")
            shutil.copy2(ROOT / "trainer/src/neural/protocol_contract.py", python_package / "protocol_contract.py")
            if asset is not None:
                (python_package / "protocol_contract.json").write_text(asset)
            python_code = (
                "from neural.protocol_contract import SUPPORTED_COMMANDS, validate_protocol_record; "
                "validate_protocol_record('|m|opaque'); print(len(SUPPORTED_COMMANDS))"
            )
            python_env = os.environ.copy()
            python_env["PYTHONPATH"] = str(sandbox / "python")
            python_run = subprocess.run(
                [sys.executable, "-c", python_code], cwd=sandbox, env=python_env,
                capture_output=True, text=True,
            )

            ts_src_dir = ROOT / "sim-core/dist/src"
            ts_copy_dir = sandbox / "sim-core/dist/src"
            ts_copy_dir.parent.mkdir(parents=True)
            shutil.copytree(ts_src_dir, ts_copy_dir)
            if asset is not None:
                ts_asset = sandbox / "trainer/src/neural/protocol_contract.json"
                ts_asset.parent.mkdir(parents=True)
                ts_asset.write_text(asset)
            ts_code = (
                "const path=require('node:path'); "
                "const c=require(process.argv[1]); "
                "require(path.join(path.dirname(process.argv[1]),'observable_state.js'))"
                ".validateRawProtocolRecord('|m|opaque'); "
                "console.log(JSON.stringify({hasM:c.SUPPORTED_RAW_COMMANDS.has('m'), size:c.SUPPORTED_RAW_COMMANDS.size}));"
            )
            ts_run = subprocess.run(
                ["node", "-e", ts_code, str(ts_copy_dir / "protocol_contract.js")],
                cwd=sandbox, capture_output=True, text=True,
            )
            outcomes[name] = {
                "python_exit": python_run.returncode,
                "python_stdout": python_run.stdout.strip(),
                "python_error": python_run.stderr.splitlines()[-1] if python_run.stderr else "",
                "typescript_exit": ts_run.returncode,
                "typescript_stdout": ts_run.stdout.strip(),
                "typescript_error": next((line for line in reversed(ts_run.stderr.splitlines()) if "Error" in line), ""),
            }
    return outcomes


def main_review():
    differential_records = [
        "|turn|١",
        '|request|{"rqid":null}',
        "|detailschange|p1a: Palafin|Palafin-Hero, L77",
        "|-endability|p1a: Pikachu|Static|[from] move: Worry Seed",
        "|-damage|p1a: Pikachu|garbage",
        "|-boost|p1a: Pikachu|banana|1000",
        "|-singleturn|p1a: Pikachu|opaque|arbitrary",
    ]
    ts_result = typescript_probe(differential_records)
    py_result = []
    for record in differential_records:
        try:
            validate_protocol_record(record)
            py_result.append(True)
        except ProtocolRecordError:
            py_result.append(False)

    bad_candidates = []
    tampered = differential_records[:2]
    for record, version, perspective, position in itertools.product(
        tampered, ("v1", "v2"), ("p1", "p2"), ("input", "successor")
    ):
        candidate = _rehashed_protocol_candidate(
            _bundle(version=version, perspective=perspective), position, record
        )
        verify_bundle_identities(candidate)
        output, error = io.StringIO(), io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(candidate))), \
                patch("sys.stdout", output), patch("sys.stderr", error):
            status = main()
        bad_candidates.append({
            "record": record,
            "version": version,
            "perspective": perspective,
            "prefix": position,
            "identity_joins_verified": True,
            "cli_status": status,
            "stdout_bytes": len(output.getvalue().encode("utf-8")),
        })

    contract = json.loads((ROOT / "trainer/src/neural/protocol_contract.json").read_text())
    fixture_mismatches = [
        {"fixture_token": item["token"], "record_token": item["record"].split("|")[1], "record": item["record"]}
        for item in contract["record_fixtures"]
        if item["token"] != item["record"].split("|")[1]
    ]
    source_records = differential_records[2:4]
    permissive_records = differential_records[4:]

    result = {
        "scope": "review findings only; no implementation acceptance",
        "runtime_matrix": [
            {"record": record, "typescript_accepts": ts_result["accepted"][index], "python_accepts": py_result[index]}
            for index, record in enumerate(differential_records)
        ],
        "fully_rehashed_publication": {
            "candidate_count": len(bad_candidates),
            "published_candidates": sum(c["cli_status"] == 0 and c["stdout_bytes"] > 0 for c in bad_candidates),
            "rejected_candidates": sum(c["cli_status"] != 0 for c in bad_candidates),
            "cases": bad_candidates,
        },
        "source_shape_false_rejections": [
            {"record": record, "typescript_rejects": not ts_result["accepted"][i + 2], "python_rejects": not py_result[i + 2]}
            for i, record in enumerate(source_records)
        ],
        "permissive_shapes_accepted_by_both": [
            record for i, record in enumerate(differential_records)
            if record in permissive_records and ts_result["accepted"][i] and py_result[i]
        ],
        "pre_filter_bypass": {
            "malformed_request_projection": ts_result["projectedMalformedRequest"],
            "unclassified_tier_projection": ts_result["projectedTier"],
        },
        "fixture_label_mismatches": fixture_mismatches,
        "loader_asset_probes": loader_asset_probes(),
    }
    if result["fully_rehashed_publication"]["published_candidates"] != 16:
        raise AssertionError("expected both malformed classes to publish in all 16 cases")
    if result["fully_rehashed_publication"]["rejected_candidates"] != 0:
        raise AssertionError("unexpectedly rejected a Python publication candidate")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main_review()
