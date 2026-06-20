"""legal-action-v7 batch 8: forced decisions and secondary chance provenance."""

import hashlib
import json
import unittest

import numpy as np

from neural.action_features import (
    ACTION_FEATURE_DIM_V7,
    ACTION_FEATURE_DIM_V7_BATCH7,
    ACTION_FEATURE_NAMES_V7,
    ACTION_FEATURE_NAMES_V7_BATCH7,
    SLICE15_FORCED_DECISION_SECONDARY_FEATURE_NAMES,
    build_action_feature_vector_v6,
    build_action_feature_vector_v7,
    slice10_typed_item_effect_feature_vector,
    slice11_typed_timing_priority_feature_vector,
    slice12_typed_hp_side_effect_feature_vector,
    slice13_typed_field_side_effect_feature_vector,
    slice14_action_risk_feature_vector,
    slice8_typed_status_stat_feature_vector,
    slice9_typed_volatile_feature_vector,
)

_BATCH7_FP = "c03b2dd345f47dae0bffefc2a0d2b5731ee7d1eb8f2bf4cabc8d415d183149f5"
_FULL_FP = "956da3d225ba9a22e05cfe774f6fa21efcbb77fa88267a8f96b1291701bf39d7"


def _fp(names):
    payload = json.dumps(list(names), ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _action(move, kind="move"):
    return {"kind": kind, "label": f"{kind}: {move}", "move": move}


def _private(**active_overrides):
    active = {
        "species": "Mew",
        "level": 80,
        "types": ["Psychic"],
        "active": True,
    }
    active.update(active_overrides)
    return {"team": [active]}


def _tactical(*, weather=None, terrain=None, own=None, opponent=None):
    return {
        "weather": weather,
        "terrain": terrain,
        "own": own or {},
        "opponent": opponent or {},
    }


def _impact(*, expected=0.40, hit=1.0, known=True):
    return {
        "available": True,
        "non_damaging": False,
        "expected_fraction": expected,
        "hit_chance": hit,
        "accuracy_known": known,
    }


def _v7(move, *, private=None, tactical=None, impact=None, kind="move"):
    return build_action_feature_vector_v7(
        _action(move, kind),
        private if private is not None else _private(),
        tactical if tactical is not None else _tactical(),
        impact,
    )


def _val(vec, name):
    return float(vec[ACTION_FEATURE_NAMES_V7.index(name)])


class Batch8SchemaIntegrityTest(unittest.TestCase):
    def test_schema_and_batch7_prefix_fingerprint(self):
        self.assertEqual(ACTION_FEATURE_DIM_V7_BATCH7, 511)
        self.assertEqual(ACTION_FEATURE_DIM_V7, 552)
        self.assertEqual(len(SLICE15_FORCED_DECISION_SECONDARY_FEATURE_NAMES), 41)
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:511], ACTION_FEATURE_NAMES_V7_BATCH7)
        self.assertEqual(_fp(ACTION_FEATURE_NAMES_V7_BATCH7), _BATCH7_FP)
        self.assertEqual(_fp(ACTION_FEATURE_NAMES_V7), _FULL_FP)

    def test_first_511_names_and_values_match_batch7(self):
        fixtures = (
            ("Surf", _private(), _tactical(), _impact()),
            ("U-turn", _private(), _tactical(), None),
            ("Iron Head", _private(), _tactical(own={"active_current_ability": "Serene Grace"}), None),
            ("Roar", _private(), _tactical(), None),
            ("Latias", _private(), _tactical(), None, "switch"),
        )
        for fixture in fixtures:
            move, private, tactical, impact, *maybe_kind = fixture
            kind = maybe_kind[0] if maybe_kind else "move"
            action = _action(move, kind)
            current = build_action_feature_vector_v7(action, private, tactical, impact)
            batch7 = np.concatenate(
                [
                    build_action_feature_vector_v6(action, private, tactical, impact),
                    slice8_typed_status_stat_feature_vector(action),
                    slice9_typed_volatile_feature_vector(action),
                    slice10_typed_item_effect_feature_vector(action, private, tactical),
                    slice11_typed_timing_priority_feature_vector(action, private, tactical),
                    slice12_typed_hp_side_effect_feature_vector(action, private, tactical),
                    slice13_typed_field_side_effect_feature_vector(action, tactical),
                    slice14_action_risk_feature_vector(action, private, tactical, impact),
                ]
            ).astype(np.float32)
            np.testing.assert_array_equal(current[:511], batch7, err_msg=move)


class PivotReplacementTest(unittest.TestCase):
    def test_damaging_pivots_create_follow_up_replacement_decision(self):
        for move in ("U-turn", "Volt Switch", "Flip Turn"):
            vec = _v7(move)
            self.assertEqual(_val(vec, "self_pivot_move"), 1.0, move)
            self.assertEqual(_val(vec, "self_pivot_requires_hit"), 1.0, move)
            self.assertEqual(_val(vec, "self_pivot_after_damage"), 1.0, move)
            self.assertEqual(_val(vec, "self_pivot_forces_replacement_decision"), 1.0, move)
            self.assertEqual(_val(vec, "self_pivot_may_fail_due_to_immunity_or_miss"), 1.0, move)

    def test_parting_shot_and_teleport_pivot_provenance(self):
        parting = _v7("Parting Shot")
        self.assertEqual(_val(parting, "self_pivot_move"), 1.0)
        self.assertEqual(_val(parting, "self_pivot_after_stat_drop"), 1.0)
        self.assertEqual(_val(parting, "self_pivot_forces_replacement_decision"), 1.0)
        teleport = _v7("Teleport")
        self.assertEqual(_val(teleport, "self_pivot_move"), 1.0)
        self.assertEqual(_val(teleport, "self_pivot_requires_hit"), 0.0)
        self.assertEqual(_val(teleport, "self_pivot_branch_known"), 1.0)


class SelfKoReplacementTest(unittest.TestCase):
    def test_self_ko_and_sacrifice_moves_force_replacement(self):
        explosion = _v7("Explosion")
        self.assertEqual(_val(explosion, "user_self_ko_move"), 1.0)
        self.assertEqual(_val(explosion, "user_self_ko_guaranteed"), 1.0)
        self.assertEqual(_val(explosion, "user_self_ko_forces_replacement_decision"), 1.0)

        memento = _v7("Memento")
        self.assertEqual(_val(memento, "user_self_ko_if_successful"), 1.0)
        self.assertEqual(_val(memento, "user_sacrifice_with_stat_drop_effect"), 1.0)

        healing_wish = _v7("Healing Wish")
        self.assertEqual(_val(healing_wish, "user_sacrifice_with_healing_wish_effect"), 1.0)

        final_gambit = _v7("Final Gambit")
        self.assertEqual(_val(final_gambit, "user_self_ko_if_successful"), 1.0)
        self.assertEqual(_val(final_gambit, "user_sacrifice_damage_based"), 1.0)

    def test_hp_cost_move_self_ko_only_when_hp_state_supports_it(self):
        high_hp = _v7("Steel Beam", private=_private(hp_fraction=1.0))
        self.assertEqual(_val(high_hp, "user_self_ko_move"), 1.0)
        self.assertEqual(_val(high_hp, "user_self_ko_if_successful"), 0.0)
        low_hp = _v7("Steel Beam", private=_private(hp_fraction=0.40))
        self.assertEqual(_val(low_hp, "user_self_ko_if_successful"), 1.0)
        self.assertEqual(_val(low_hp, "user_self_ko_forces_replacement_decision"), 1.0)


class PhazingItemTriggerTest(unittest.TestCase):
    def test_phazing_moves_mark_target_forced_switch_pressure(self):
        for move in ("Roar", "Whirlwind"):
            vec = _v7(move)
            self.assertEqual(_val(vec, "forces_target_switch"), 1.0, move)
            self.assertEqual(_val(vec, "forced_target_switch_random"), 1.0, move)
            self.assertEqual(_val(vec, "phazing_priority_negative"), 1.0, move)
            self.assertEqual(_val(vec, "forced_switch_pressure_present"), 1.0, move)
        for move in ("Dragon Tail", "Circle Throw"):
            vec = _v7(move)
            self.assertEqual(_val(vec, "forces_target_switch_if_hits"), 1.0, move)
            self.assertEqual(_val(vec, "phazing_blocked_by_substitute_possible"), 1.0, move)

    def test_item_trigger_switches_require_known_item_state(self):
        eject_pack = _v7("Draco Meteor", private=_private(item="Eject Pack"))
        self.assertEqual(_val(eject_pack, "user_item_may_force_self_switch"), 1.0)
        self.assertEqual(_val(eject_pack, "eject_pack_possible"), 1.0)

        unknown_pack = _v7("Draco Meteor")
        self.assertEqual(_val(unknown_pack, "eject_pack_possible"), 0.0)
        self.assertEqual(_val(unknown_pack, "item_trigger_branch_unknown"), 1.0)

        eject_button = _v7("Surf", tactical=_tactical(opponent={"active_item": "Eject Button", "active_item_state": "held"}))
        self.assertEqual(_val(eject_button, "target_item_may_force_target_switch"), 1.0)
        self.assertEqual(_val(eject_button, "eject_button_possible"), 1.0)

        red_card = _v7("Surf", tactical=_tactical(opponent={"active_item": "Red Card", "active_item_state": "held"}))
        self.assertEqual(_val(red_card, "red_card_possible"), 1.0)
        self.assertEqual(_val(red_card, "item_trigger_branch_known"), 1.0)


class SecondaryChanceModifierTest(unittest.TestCase):
    def test_ordinary_move_has_zero_forced_fields_and_no_secondary(self):
        vec = _v7("Surf")
        for name in SLICE15_FORCED_DECISION_SECONDARY_FEATURE_NAMES:
            self.assertEqual(_val(vec, name), 0.0, name)

    def test_iron_head_flinch_and_serene_grace_modifier(self):
        normal = _v7("Iron Head")
        self.assertEqual(_val(normal, "secondary_chance_base_known"), 1.0)
        self.assertAlmostEqual(_val(normal, "secondary_chance_base"), 0.30, places=5)
        self.assertAlmostEqual(_val(normal, "flinch_chance_modified"), 0.30, places=5)

        serene = _v7("Iron Head", private=_private(ability="Serene Grace"))
        self.assertEqual(_val(serene, "secondary_chance_modifier_serene_grace"), 1.0)
        self.assertEqual(_val(serene, "secondary_chance_modified_known"), 1.0)
        self.assertAlmostEqual(_val(serene, "flinch_chance_modified"), 0.60, places=5)

    def test_status_and_stat_drop_secondary_chances_modify(self):
        body_slam = _v7("Body Slam")
        self.assertAlmostEqual(_val(body_slam, "status_chance_modified"), 0.30, places=5)
        serene_body_slam = _v7("Body Slam", private=_private(ability="Serene Grace"))
        self.assertAlmostEqual(_val(serene_body_slam, "status_chance_modified"), 0.60, places=5)
        crunch = _v7("Crunch")
        self.assertAlmostEqual(_val(crunch, "stat_drop_chance_modified"), 0.20, places=5)

    def test_blockers_and_sheer_force_require_known_state(self):
        shield = _v7("Iron Head", tactical=_tactical(opponent={"active_current_ability": "Shield Dust"}))
        self.assertEqual(_val(shield, "secondary_chance_blocked_by_shield_dust_possible"), 1.0)
        self.assertEqual(_val(shield, "flinch_chance_modified"), 0.0)

        cloak = _v7("Iron Head", tactical=_tactical(opponent={"active_item": "Covert Cloak", "active_item_state": "held"}))
        self.assertEqual(_val(cloak, "secondary_chance_blocked_by_covert_cloak_possible"), 1.0)
        self.assertEqual(_val(cloak, "flinch_chance_modified"), 0.0)

        sheer_force = _v7("Iron Head", private=_private(ability="Sheer Force"))
        self.assertEqual(_val(sheer_force, "secondary_removed_by_sheer_force_possible"), 1.0)
        self.assertEqual(_val(sheer_force, "flinch_chance_modified"), 0.0)


if __name__ == "__main__":
    unittest.main()
