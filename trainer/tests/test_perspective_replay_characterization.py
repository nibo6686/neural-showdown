"""Supplied replay characterization, not knowledge assurance or dataset production."""

import copy
import hashlib
import html
import json
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from neural import compare_action_rankers as loader
from neural.build_live_private_value_dataset import (
    _reconstructed_completed_private_teams,
    _reconstructed_private_state_for_side,
    _trajectory_prefix_for_training,
)
from neural.parse_replay_logs import parse_protocol_log

FIXTURES = Path(__file__).parent / "fixtures/perspective-replay"
LEDGER = json.loads((FIXTURES / "expected-ledger.json").read_text(encoding="utf-8"))
REQUIREMENTS = os.environ.get("PERSPECTIVE_REPLAY_REQUIREMENTS") == "1"


def source_records(filename):
    """Independent original block extraction; retain source transport evidence."""
    text = (FIXTURES / filename).read_text(encoding="utf-8")
    block = re.search(r'<script[^>]*class="battle-log-data"[^>]*>(.*?)</script>', text, re.S).group(1)
    return [html.unescape(line.strip()) for line in block.splitlines() if line.strip().startswith("|")]


def report(rows):
    output = os.environ.get("PERSPECTIVE_REPLAY_REPORT")
    if output:
        Path(output).write_text(json.dumps({"readiness": False, "mode": "semantic requirements" if REQUIREMENTS else "characterization", "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class SuppliedReplayCharacterizationTest(unittest.TestCase):
    def test_loader_and_legacy_reconstruction(self):
        rows = []
        for fixture in LEDGER["fixtures"]:
            path = FIXTURES / fixture["filename"]
            raw = source_records(fixture["filename"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), fixture["sha256"])
            self.assertEqual(len(raw), fixture["record_count"])
            with patch.object(loader, "load_replay_trajectory", side_effect=AssertionError("network/trajectory fallback forbidden")), \
                 patch.object(loader, "_load_ranker", side_effect=AssertionError("checkpoint forbidden")), \
                 patch.object(loader, "torch_load", side_effect=AssertionError("checkpoint forbidden")), \
                 patch.object(loader, "_score_with_ranker", side_effect=AssertionError("scoring forbidden")):
                trajectory = loader._load_replay(str(path), replay_dir=FIXTURES, trajectories_path=path, format_name=fixture["format"])
            decoded = [record.replace("\\/", "/") for record in raw]
            self.assertEqual(trajectory["protocol_log"], decoded)
            self.assertEqual(trajectory["winner"], "hasklne")
            self.assertEqual(trajectory["winner_side"], "p1")
            self.assertEqual(trajectory["p1"], "hasklne")
            # Preserve original identity across OU's later empty departure record.
            self.assertEqual(trajectory["p2"], fixture["players"]["p2"])
            rows.append({"fixture": fixture["key"], "stage": "loader/player identity", "index": len(raw) - 1, "record": raw[-1], "expected": fixture["players"]["p2"], "actual": trajectory["p2"], "classification": "positive" if trajectory["p2"] == fixture["players"]["p2"] else "identity error"})
            self.assertEqual(trajectory["turns"][0]["turn"], 0)
            self.assertEqual(raw[8], "|rated|")
            completed = _reconstructed_completed_private_teams(trajectory)
            for owner in ("p1", "p2"):
                # Exact existing caller: full trajectory + through_turn + full-source completed teams.
                state = _reconstructed_private_state_for_side(trajectory, side=owner, through_turn=0, completed_teams=copy.deepcopy(completed))
                rows.append({"fixture": fixture["key"], "owner": owner, "stage": "legacy caller shape", "through_turn": 0, "actual": state, "classification": "unverified reconstruction; NOT authentic request", "unknown_obligations": ["integer HP", "PP/maxPP", "legal actions", "starting attribution"]})
                active = state["active_moves"]
                rows.append({"fixture": fixture["key"], "owner": owner, "stage": "legacy PP certainty", "expected": None, "actual": [{k: m[k] for k in ("name", "pp", "maxpp")} for m in active], "classification": "fabricated certainty" if active else "not observable"})
                prefix = _trajectory_prefix_for_training(trajectory, 0)
                self.assertTrue(all(t["turn"] <= 0 for t in prefix["turns"]))
                rows.append({"fixture": fixture["key"], "owner": owner, "stage": "turn-only cutoff", "actual_cursor": len(prefix["protocol_log"]), "classification": "cannot express same-turn record cutoff"})
            # Preserve each raw HP boundary versus intended fraction from independent rendering.
            for entry in fixture["entries"]:
                if entry["property"] != "hp_text":
                    continue
                event = next(e for t in trajectory["turns"] for e in t["events"] if e.get("raw") == decoded[entry["index"]])
                expected_ratio = int(entry["expected"].split('/')[0]) / int(entry["expected"].split('/')[1])
                self.assertEqual(event.get("hp_fraction"), expected_ratio)
                rows.append({"fixture": fixture["key"], **entry, "imported_record": decoded[entry["index"]], "stage": "loader -> parser HP", "actual": event.get("hp_fraction"), "expected_ratio": expected_ratio, "classification": "positive" if event.get("hp_fraction") == expected_ratio else "load/HP transport failure"})
            # Complete teams do not observe passive [from] revelations.
            for subject, expected, evidence_index, prop in (("Skuntank", "Life Orb", 39, "item"), ("Toxapex", "Leftovers", 149, "item"), ("Skuntank", "Aftermath", 42, "ability")) if fixture["key"] == "random" else (("Gliscor", "Poison Heal", 124, "ability"), ("Ting-Lu", "Rocky Helmet", 224, "item")):
                side = "p2" if subject in ("Gliscor", "Ting-Lu") else "p1"
                observed = completed[side][subject][prop]
                rows.append({"fixture": fixture["key"], "owner": side, "index": evidence_index, "cursor": evidence_index+1, "record": raw[evidence_index], "subject": subject, "property": prop, "expected": expected, "actual": observed, "classification": "positive" if observed == expected else "lost revelation"})
        report(rows)
        self.assertFalse(any(r["classification"] == "load/HP transport failure" for r in rows))
        self.assertTrue(any(r["classification"] == "fabricated certainty" for r in rows))
        if REQUIREMENTS:
            self.assertEqual([r for r in rows if r["classification"] in ("identity error", "load/HP transport failure", "fabricated certainty", "lost revelation")], [], "Preserved source-backed requirement reds; see matrix")

    def test_synthetic_original_attribution_and_suffix_noninterference(self):
        rows = []
        for owner, opponent in (("p1", "p2"), ("p2", "p1")):
            raw = [f'|switch|{owner}a: Ditto|Ditto|100/100', f'|switch|{opponent}a: Target|Gengar|100/100', '|turn|1', f'|-transform|{owner}a: Ditto|{opponent}a: Target', f'|move|{owner}a: Ditto|Shadow Ball|{opponent}a: Target', '|turn|2', f'|-item|{owner}a: Ditto|Leftovers|[from] move: Trick']
            full = parse_protocol_log(raw, format_name="gen9randombattle")
            teams = _reconstructed_completed_private_teams(full)
            state = _reconstructed_private_state_for_side(full, side=owner, through_turn=0, completed_teams=copy.deepcopy(teams))
            expected = {"moves": [], "item": None}
            observed = {"moves": sorted(teams[owner]["Ditto"]["moves"]), "item": teams[owner]["Ditto"]["item"]}
            rows.append({"synthetic": "Transform/acquisition", "owner": owner, "source": raw, "property": "eligible starting-original revelations (empty is not a known empty original loadout)", "expected": expected, "actual": observed, "classification": "positive" if observed == expected else "chronology leak / invalid original attribution"})
            altered = parse_protocol_log([r.replace("Shadow Ball", "Sludge Bomb").replace("Leftovers", "Life Orb") for r in raw], format_name="gen9randombattle")
            changed_state = _reconstructed_private_state_for_side(altered, side=owner, through_turn=0, completed_teams=_reconstructed_completed_private_teams(altered))
            rows.append({"synthetic": "both-owner causal suffix", "owner": owner, "cursor": 3, "expected": state, "actual": changed_state, "classification": "chronology leak" if state != changed_state else "positive"})
            # Public turn-zero prefix itself remains causal; completed-team current overlay does not.
            self.assertEqual(_trajectory_prefix_for_training(full, 0)["protocol_log"], _trajectory_prefix_for_training(altered, 0)["protocol_log"])
            duplicate = [f'|switch|{owner}a: Pikachu|Pikachu|100/100', f'|move|{owner}a: Pikachu|Thunderbolt|{opponent}a: Target', f'|switch|{owner}a: Pikachu|Pikachu|100/100', f'|move|{owner}a: Pikachu|Surf|{opponent}a: Target']
            collapsed = _reconstructed_completed_private_teams(parse_protocol_log(duplicate))
            rows.append({"synthetic": "duplicate species/nickname ambiguity", "owner": owner, "source": duplicate, "actual": sorted(collapsed[owner]["Pikachu"]["moves"]), "expected": "appearance relation unresolved; may be reentry or a duplicate; no proven cross-Pokemon merge", "classification": "unresolved identity control"})
        output = os.environ.get("PERSPECTIVE_REPLAY_REPORT")
        if output:
            existing = json.loads(Path(output).read_text(encoding="utf-8"))
            existing["synthetic_rows"] = rows
            Path(output).write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.assertTrue(all(r["classification"] == "chronology leak" for r in rows if r["synthetic"] == "both-owner causal suffix"))
        if REQUIREMENTS:
            self.assertEqual([r for r in rows if r["classification"] in ("chronology leak", "chronology leak / invalid original attribution")], [], "Synthetic attribution requirements remain red")


if __name__ == "__main__":
    unittest.main()
