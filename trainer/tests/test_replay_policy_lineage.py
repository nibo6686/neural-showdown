import copy
import gzip
import json

import pytest

from neural.build_replay_policy_dataset import (
    build_public_replay_policy_dataset,
    examples_from_policy_trajectory,
)
from neural.dataset_lineage import DatasetLineageError, validate_record_prefix, validate_records
from neural.parse_replay_logs import parse_protocol_log


MOVE = "|move|p1a: Pivot|U-turn|p2a: Target"
SWITCH = "|switch|p1a: Bench|Pikachu, L80|100/100"
INITIAL = [
    "|player|p1|Alice|1|",
    "|player|p2|Bob|2|",
    "|teamsize|p1|6",
    "|teamsize|p2|6",
    "|switch|p1a: Pivot|Scizor, L80|100/100",
    "|switch|p2a: Target|Blissey, L80|100/100",
    "|turn|1",
]


def trajectory(lines):
    # Constructed protocol evidence, not a source-engine/generated-team witness.
    return parse_protocol_log(
        lines, replay_id="policy-boundary-fixture", format_name="gen9randombattle",
        source_path="synthetic://policy-boundary-fixture",
    )


def examples(lines):
    rows, reason = examples_from_policy_trajectory(trajectory(lines))
    assert reason is None
    for row in rows:
        record = row["dataset_record"]
        validate_record_prefix(record, lines[:record["observation_cursor"]])
    validate_records([row["dataset_record"] for row in rows])
    return rows


def publish(tmp_path, trajectories, output=None):
    inputs = tmp_path / "trajectories.jsonl.gz"
    with gzip.open(inputs, "wt", encoding="utf-8") as handle:
        for item in trajectories:
            handle.write(json.dumps(item) + "\n")
    return build_public_replay_policy_dataset(
        trajectories_path=inputs, replay_dir=tmp_path / "unused",
        output_path=output or tmp_path / "policy.jsonl.gz",
        report_json_path=tmp_path / "report.json", report_md_path=tmp_path / "report.md",
    )


def test_same_turn_move_switch_distinct_lineage_and_publication(tmp_path):
    lines = INITIAL + [MOVE, "|-damage|p2a: Target|80/100", SWITCH, "|win|Alice"]
    source = trajectory(lines)
    before = copy.deepcopy(source)
    rows = examples(lines)
    actions = [row for row in rows if row["perspective"] == "p1" and row["turn"] == 1]
    assert [row["action_type"] for row in actions] == ["move", "switch"]
    records = [row["dataset_record"] for row in actions]
    assert [record["observation_cursor"] for record in records] == [lines.index(MOVE), lines.index(SWITCH)]
    assert records[0]["record_id"] != records[1]["record_id"]
    assert records[0]["observation_prefix_hash"] != records[1]["observation_prefix_hash"]
    assert source == before
    report = publish(tmp_path, [source])
    assert report["examples"] == 4
    with gzip.open(tmp_path / "policy.jsonl.gz", "rt", encoding="utf-8") as handle:
        published = [json.loads(line) for line in handle]
    assert published == rows
    assert len({row["dataset_record"]["record_id"] for row in published}) == 4


def test_genuine_duplicate_rejected_before_publication(tmp_path):
    lines = INITIAL + [MOVE, "|win|Alice"]
    record = examples(lines)[-1]["dataset_record"]
    with pytest.raises(DatasetLineageError, match="duplicate record identity"):
        validate_records([record, copy.deepcopy(record)])
    source = trajectory(lines)
    before = copy.deepcopy(source)
    output = tmp_path / "policy.jsonl.gz"
    output.write_bytes(b"existing-output-preserved")
    with pytest.raises(DatasetLineageError, match="duplicate record identity"):
        publish(tmp_path, [source, copy.deepcopy(source)], output)
    assert output.read_bytes() == b"existing-output-preserved"
    assert not (tmp_path / "report.json").exists()
    assert source == before


def test_later_same_turn_suffix_cannot_change_earlier_boundary():
    early = INITIAL + [MOVE, "|win|Alice"]
    later = INITIAL + [MOVE, "|-damage|p2a: Target|80/100", SWITCH,
                       "|move|p1a: Bench|Thunderbolt|p2a: Target", "|win|Alice"]
    first = next(row for row in examples(early) if row["turn"] == 1)
    extended = next(row for row in examples(later) if row["turn"] == 1)
    assert first == extended
    cursor = first["dataset_record"]["observation_cursor"]
    assert early[:cursor] == later[:cursor] == INITIAL
    assert MOVE not in early[:cursor]


def test_single_action_and_unverifiable_boundary_control():
    lines = INITIAL + [MOVE, "|win|Alice"]
    rows = examples(lines)
    actions = [row for row in rows if row["turn"] == 1]
    assert len(actions) == 1
    assert actions[0]["dataset_record"]["observation_cursor"] == len(INITIAL)
    source = trajectory(lines)
    missing = copy.deepcopy(source)
    missing.pop("protocol_log")
    stale = copy.deepcopy(source)
    stale["turns"][-1]["events"][0]["raw"] = "|move|p1a: Pivot|Tackle|p2a: Target"
    omitted = copy.deepcopy(source)
    omitted["turns"][-1]["events"].pop(0)
    for candidate in (missing, stale, omitted):
        before = copy.deepcopy(candidate)
        rejected, reason = examples_from_policy_trajectory(candidate)
        assert rejected == []
        assert reason.startswith("unverifiable_action_boundaries:")
        assert candidate == before
