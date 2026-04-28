import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from neural.live_action_recommender import legal_action_candidates, recommend_actions
from neural.live_opponent_beliefs import build_opponent_beliefs
from neural.live_private_features import FEATURE_DIM
from neural.live_private_state import extract_private_side_state
from neural.sim_branch_evaluator import evaluate_actions
from neural.tactical_state import build_tactical_state, tactical_action_flags


def _request(*, moves, side_pokemon=None, active_extra=None, force_switch=False):
    active_extra = active_extra or {}
    return {
        "forceSwitch": [force_switch] if force_switch else None,
        "side": {
            "id": "p1",
            "pokemon": side_pokemon
            or [
                {
                    "ident": "p1: Pikachu",
                    "details": "Pikachu, L80",
                    "condition": "100/100",
                    "active": True,
                    "stats": {"spe": 216, "atk": 146, "spa": 196, "def": 120, "spd": 140},
                    "teraType": "Electric",
                },
                {"ident": "p1: Charizard", "details": "Charizard, L80", "condition": "100/100", "active": False},
            ],
        },
        "active": [{**active_extra, "moves": moves}],
    }


def _trace(request, legal_actions, protocol=None, view=None):
    return {
        "replay_id": "mechanics-audit",
        "format": "gen9randombattle",
        "protocol_log": protocol
        or [
            "|player|p1|Alice",
            "|player|p2|Bob",
            "|turn|1",
            "|switch|p1a: Pikachu|Pikachu, L80|100/100",
            "|switch|p2a: Charizard|Charizard, L80|100/100",
        ],
        "turns": [{"turn": 1, "steps": [{"step_index": 0, "view": view or {}, "request": request, "legal_actions": legal_actions}]}],
    }


class MechanicsLegalityTest(unittest.TestCase):
    def test_disabled_zero_pp_trapped_and_force_switch_are_respected(self):
        request = _request(
            moves=[
                {"move": "Thunderbolt", "id": "thunderbolt", "pp": 10, "maxpp": 15, "disabled": False},
                {"move": "Thunder Wave", "id": "thunderwave", "pp": 20, "maxpp": 20, "disabled": True},
                {"move": "Quick Attack", "id": "quickattack", "pp": 0, "maxpp": 30, "disabled": False},
            ],
            active_extra={"trapped": True},
        )
        payload = type("Payload", (), {"request": request, "legal_actions": []})()
        candidates = legal_action_candidates(payload)
        by_label = {row["label"]: row for row in candidates}
        self.assertTrue(by_label["move: Thunder Wave"]["disabled"])
        self.assertTrue(by_label["move: Quick Attack"]["disabled"])
        self.assertFalse(any(row["kind"] == "switch" for row in candidates))

        force_payload = type("Payload", (), {"request": _request(moves=[], force_switch=True), "legal_actions": []})()
        self.assertTrue(all(row["kind"] == "switch" for row in legal_action_candidates(force_payload)))

    def test_disabled_and_zero_pp_moves_are_not_recommended(self):
        request = _request(
            moves=[
                {"move": "Thunderbolt", "id": "thunderbolt", "pp": 10, "maxpp": 15, "disabled": False},
                {"move": "Thunder Wave", "id": "thunderwave", "pp": 20, "maxpp": 20, "disabled": True},
                {"move": "Quick Attack", "id": "quickattack", "pp": 0, "maxpp": 30, "disabled": False},
            ]
        )
        payload = type("Payload", (), {"request": request, "legal_actions": []})()
        private_state = extract_private_side_state(request_payload=request, legal_actions=[], player_hint="p1")
        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "neural.live_action_recommender.DEFAULT_ACTION_RANKER_PATH", Path(tmpdir) / "missing.pt"
        ):
            report = recommend_actions(
                payload=payload,
                private_state=private_state,
                opponent_belief={"opponents": []},
                trajectory={"turns": []},
                public_features=np.zeros(31, dtype=np.float32),
                live_features=np.zeros(FEATURE_DIM, dtype=np.float32),
                current_value=0.0,
                value_model=None,
                value_metadata={},
                policy_loader=lambda: (None, {"warning": "missing"}),
                device=torch.device("cpu"),
            )
        self.assertTrue(report["top_actions"])
        self.assertFalse(any(row["label"] in {"move: Thunder Wave", "move: Quick Attack"} for row in report["top_actions"]))

    def test_taunt_encore_choice_and_locked_move_are_exposed_as_restrictions(self):
        request = _request(moves=[{"move": "Thunder Wave", "id": "thunderwave", "pp": 20, "maxpp": 20, "disabled": False}])
        legal = [{"kind": "move", "label": "move: Thunder Wave", "choice": "move 1", "index": 0, "slot": 1, "move": "Thunder Wave"}]
        protocol = [
            "|turn|1",
            "|switch|p1a: Pikachu|Pikachu, L80|100/100",
            "|switch|p2a: Kingambit|Kingambit, L80|100/100",
            "|-start|p1a: Pikachu|move: Taunt",
            "|-start|p1a: Pikachu|Encore",
            "|-start|p1a: Pikachu|move: Outrage",
        ]
        results = evaluate_actions({"trace": _trace(request, legal, protocol=protocol)}, "p1", legal, rollout_config={"rollout_mode": "approximate", "rollouts_per_action": 8})
        warnings = set(results[0]["approximation_warnings"])
        self.assertIn("taunt_blocks_status", warnings)
        self.assertIn("encore_active", warnings)
        self.assertIn("locked_move_active", warnings)


class MechanicsSpeedDamageTest(unittest.TestCase):
    def test_priority_and_trick_room_speed_diagnostics(self):
        request = _request(
            moves=[
                {"move": "Quick Attack", "id": "quickattack", "pp": 30, "maxpp": 30, "disabled": False},
                {"move": "Thunderbolt", "id": "thunderbolt", "pp": 10, "maxpp": 15, "disabled": False},
            ],
            side_pokemon=[
                {
                    "ident": "p1: Pikachu",
                    "details": "Pikachu, L80",
                    "condition": "100/100",
                    "active": True,
                    "stats": {"spe": 50, "atk": 146, "spa": 196},
                }
            ],
        )
        legal = [
            {"kind": "move", "label": "move: Quick Attack", "choice": "move 1", "index": 0, "slot": 1, "move": "Quick Attack"},
            {"kind": "move", "label": "move: Thunderbolt", "choice": "move 2", "index": 1, "slot": 2, "move": "Thunderbolt"},
        ]
        view = {"opponent_team": [{"species": "Charizard", "types": ["Fire", "Flying"], "hp_fraction": 0.1, "stats": {"spe": 200}}]}
        results = evaluate_actions({"trace": _trace(request, legal, view=view)}, "p1", legal, rollout_config={"rollout_mode": "approximate", "rollouts_per_action": 16})
        qa = next(row for row in results if row["label"] == "move: Quick Attack")
        self.assertTrue(qa["diagnostics"]["speed_order"]["likely_moves_first"])
        self.assertEqual(qa["diagnostics"]["speed_order"]["move_priority"], 1)

        protocol = ["|turn|1", "|switch|p1a: Pikachu|Pikachu, L80|100/100", "|switch|p2a: Deoxys-Speed|Deoxys-Speed, L80|100/100", "|-fieldstart|move: Trick Room"]
        tr_results = evaluate_actions({"trace": _trace(request, [legal[1]], protocol=protocol, view=view)}, "p1", [legal[1]], rollout_config={"rollout_mode": "approximate", "rollouts_per_action": 8})
        self.assertTrue(tr_results[0]["diagnostics"]["speed_order"]["trick_room_active"])
        self.assertTrue(tr_results[0]["diagnostics"]["speed_order"]["likely_moves_first"])

    def test_damage_diagnostics_rank_effective_ko_and_burn_penalty(self):
        request = _request(
            moves=[
                {"move": "Thunderbolt", "id": "thunderbolt", "pp": 10, "maxpp": 15, "disabled": False},
                {"move": "Quick Attack", "id": "quickattack", "pp": 30, "maxpp": 30, "disabled": False},
            ]
        )
        legal = [
            {"kind": "move", "label": "move: Thunderbolt", "choice": "move 1", "index": 0, "slot": 1, "move": "Thunderbolt"},
            {"kind": "move", "label": "move: Quick Attack", "choice": "move 2", "index": 1, "slot": 2, "move": "Quick Attack"},
        ]
        view = {"opponent_team": [{"species": "Charizard", "types": ["Fire", "Flying"], "hp_fraction": 0.25, "stats": {"spd": 100, "def": 100}}]}
        results = evaluate_actions({"trace": _trace(request, legal, view=view)}, "p1", legal, rollout_config={"rollout_mode": "approximate", "rollouts_per_action": 32})
        by_label = {row["label"]: row for row in results}
        self.assertGreater(by_label["move: Thunderbolt"]["final_score"], by_label["move: Quick Attack"]["final_score"])
        self.assertGreaterEqual(by_label["move: Thunderbolt"]["diagnostics"]["damage"]["type_effectiveness"], 2.0)
        self.assertGreater(by_label["move: Thunderbolt"]["diagnostics"]["damage"]["estimated_ko_chance"], 0.0)

        burned_protocol = ["|turn|1", "|switch|p1a: Pikachu|Pikachu, L80|100/100 brn", "|switch|p2a: Blissey|Blissey, L80|100/100"]
        burn_results = evaluate_actions({"trace": _trace(request, [legal[1]], protocol=burned_protocol, view=view)}, "p1", [legal[1]], rollout_config={"rollout_mode": "approximate", "rollouts_per_action": 8})
        self.assertTrue(burn_results[0]["diagnostics"]["damage"]["burn_attack_penalty"])

    def test_tera_boosted_ko_can_outrank_non_tera(self):
        request = _request(
            moves=[{"move": "Thunderbolt", "id": "thunderbolt", "pp": 10, "maxpp": 15, "disabled": False}],
            active_extra={"canTerastallize": "Electric"},
        )
        legal = [
            {"kind": "move", "label": "move: Thunderbolt", "choice": "move 1", "index": 0, "slot": 1, "move": "Thunderbolt"},
            {"kind": "move_tera", "label": "move_tera: Thunderbolt", "choice": "move 1 terastallize", "index": 4, "slot": 1, "move": "Thunderbolt", "can_tera": True, "tera_type": "Electric"},
        ]
        view = {"opponent_team": [{"species": "Charizard", "types": ["Fire", "Flying"], "hp_fraction": 0.4}]}
        results = evaluate_actions({"trace": _trace(request, legal, view=view)}, "p1", legal, rollout_config={"rollout_mode": "approximate", "rollouts_per_action": 32})
        by_label = {row["label"]: row for row in results}
        self.assertGreater(by_label["move_tera: Thunderbolt"]["final_score"], by_label["move: Thunderbolt"]["final_score"])


class MechanicsAbilityItemHazardTest(unittest.TestCase):
    def test_ability_based_blockers_are_flagged(self):
        cases = [
            ("Surf", "Water", "Water Absorb", "known_immunity_or_blocked"),
            ("Thunderbolt", "Electric", "Lightning Rod", "known_immunity_or_blocked"),
            ("Giga Drain", "Grass", "Sap Sipper", "known_immunity_or_blocked"),
            ("Thunder Wave", "Electric", "Good as Gold", "known_immunity_or_blocked"),
            ("Hyper Voice", "Normal", "Soundproof", "known_immunity_or_blocked"),
            ("Shadow Ball", "Ghost", "Bulletproof", "known_immunity_or_blocked"),
        ]
        for move, move_type, ability, expected in cases:
            with self.subTest(move=move, ability=ability):
                state = build_tactical_state(
                    ["|turn|1", "|switch|p1a: Pikachu|Pikachu, L80|100/100", "|switch|p2a: Kommo-o|Kommo-o, L80|100/100", f"|-ability|p2a: Kommo-o|{ability}"],
                    perspective_side="p1",
                )
                flags = tactical_action_flags({"kind": "move", "label": f"move: {move}"}, tactical_state=state, move_type=move_type)
                self.assertIn(expected, flags)

    def test_prankster_status_into_dark_is_blocked(self):
        state = build_tactical_state(["|turn|1", "|switch|p1a: Grimmsnarl|Grimmsnarl, L80|100/100", "|switch|p2a: Kingambit|Kingambit, L80|100/100"], perspective_side="p1")
        private = {"player_side": "p1", "team": [{"species": "Grimmsnarl", "active": True, "ability": "Prankster"}]}
        flags = tactical_action_flags({"kind": "move", "label": "move: Thunder Wave"}, private_state=private, tactical_state=state)
        self.assertIn("prankster_status_blocked_by_dark", flags)

    def test_hazard_switch_diagnostics_cover_boots_grounding_and_faint_risk(self):
        side_pokemon = [
            {"ident": "p1: Pikachu", "details": "Pikachu, L80", "condition": "100/100", "active": True},
            {"ident": "p1: Charizard", "details": "Charizard, L80", "condition": "10/100", "active": False, "item": "Heavy-Duty Boots"},
            {"ident": "p1: Raichu", "details": "Raichu, L80", "condition": "10/100", "active": False},
        ]
        request = _request(moves=[{"move": "Thunderbolt", "pp": 10, "maxpp": 15, "disabled": False}], side_pokemon=side_pokemon)
        legal = [
            {"kind": "switch", "label": "switch: Charizard", "choice": "switch 2", "index": 8},
            {"kind": "switch", "label": "switch: Raichu", "choice": "switch 3", "index": 9},
        ]
        protocol = ["|turn|1", "|switch|p1a: Pikachu|Pikachu, L80|100/100", "|-sidestart|p1: Alice|move: Stealth Rock", "|-sidestart|p1: Alice|move: Spikes", "|-sidestart|p1: Alice|move: Toxic Spikes", "|-sidestart|p1: Alice|move: Sticky Web"]
        results = evaluate_actions({"trace": _trace(request, legal, protocol=protocol)}, "p1", legal, rollout_config={"rollout_mode": "approximate", "rollouts_per_action": 8})
        by_label = {row["label"]: row for row in results}
        self.assertTrue(by_label["switch: Charizard"]["diagnostics"]["switch_hazards"]["boots_prevent_hazards"])
        self.assertEqual(by_label["switch: Charizard"]["diagnostics"]["switch_hazards"]["switch_hazard_damage"], 0.0)
        self.assertTrue(by_label["switch: Raichu"]["diagnostics"]["switch_hazards"]["toxic_spikes_poison_risk"])
        self.assertTrue(by_label["switch: Raichu"]["diagnostics"]["switch_hazards"]["faint_on_entry_risk"])

    def test_focus_sash_eviolite_life_orb_and_leftovers_are_represented(self):
        request = _request(
            moves=[{"move": "Thunderbolt", "id": "thunderbolt", "pp": 10, "maxpp": 15, "disabled": False}],
            side_pokemon=[{"ident": "p1: Pikachu", "details": "Pikachu, L80", "condition": "100/100", "active": True, "item": "Life Orb"}],
        )
        legal = [{"kind": "move", "label": "move: Thunderbolt", "choice": "move 1", "index": 0, "slot": 1, "move": "Thunderbolt"}]
        view = {"opponent_team": [{"species": "Charizard", "types": ["Fire", "Flying"], "hp_fraction": 1.0, "item": "Focus Sash"}]}
        result = evaluate_actions({"trace": _trace(request, legal, view=view)}, "p1", legal, rollout_config={"rollout_mode": "approximate", "rollouts_per_action": 8})[0]
        self.assertEqual(result["diagnostics"]["damage"]["item_modifier"], 1.3)
        self.assertLess(result["diagnostics"]["damage"]["estimated_damage_range"][1], 1.0)


class MechanicsDurationsPpBeliefTest(unittest.TestCase):
    def test_field_duration_snapshots_track_start_end_and_remaining(self):
        state = build_tactical_state(
            [
                "|turn|1",
                "|-fieldstart|move: Trick Room",
                "|-sidestart|p1: Alice|move: Tailwind",
                "|-sidestart|p1: Alice|move: Reflect",
                "|-weather|RainDance",
                "|turn|3",
            ],
            perspective_side="p1",
        )
        self.assertEqual(state["field_durations"]["trickroom"]["turns_since_started"], 2)
        self.assertEqual(state["field_durations"]["weather"]["effect"], "raindance")
        self.assertIn("tailwind", state["own"]["side_condition_durations"])
        self.assertIn("reflect", state["own"]["side_condition_durations"])

        ended = build_tactical_state(["|turn|1", "|-fieldstart|move: Trick Room", "|turn|2", "|-fieldend|move: Trick Room"], perspective_side="p1")
        self.assertNotIn("trickroom", ended["field_effects"])

    def test_public_pp_is_inferred_not_exact(self):
        state = build_tactical_state(["|turn|1", "|switch|p2a: Banette|Banette, L80|100/100", "|move|p2a: Banette|Gunk Shot|p1a: Kingambit"], perspective_side="p1")
        pp = state["opponent"]["inferred_pp_by_species_move"]["Banette"]["gunkshot"]
        self.assertEqual(pp["provenance"], "inferred_from_public_usage")
        self.assertEqual(state["opponent"]["exact_pp_by_species_move"]["Banette"], {})

    def test_opponent_belief_filters_and_relaxes_with_warning(self):
        index = {
            "pikachu": [
                {"species": "Pikachu", "moves": ["Thunderbolt", "Surf"], "items": ["Light Ball"], "abilities": ["Static"], "tera_types": ["Electric"], "weight": 2.0},
                {"species": "Pikachu", "moves": ["Quick Attack"], "items": ["Choice Band"], "abilities": ["Lightning Rod"], "tera_types": ["Normal"], "weight": 1.0},
            ]
        }
        trajectory = {"turns": [{"turn": 1, "events": [{"type": "move", "side": "p2", "actor": "p2a: Pikachu", "move": "Thunderbolt"}]}]}
        with patch("neural.live_opponent_beliefs.load_randbats_index", return_value=(index, "mock", [])):
            beliefs = build_opponent_beliefs(protocol_log=[], trajectory=trajectory, player_side="p1")
        self.assertEqual(beliefs["opponents"][0]["candidate_count"], 1)

        impossible = {"turns": [{"turn": 1, "events": [{"type": "move", "side": "p2", "actor": "p2a: Pikachu", "move": "V-create"}]}]}
        with patch("neural.live_opponent_beliefs.load_randbats_index", return_value=(index, "mock", [])):
            relaxed = build_opponent_beliefs(protocol_log=[], trajectory=impossible, player_side="p1")
        self.assertTrue(relaxed["opponents"][0]["filter_relaxed"])
        self.assertTrue(any("relaxed_opponent_set_filters" in warning for warning in relaxed["warnings"]))


if __name__ == "__main__":
    unittest.main()
