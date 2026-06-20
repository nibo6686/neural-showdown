"""legal-action-v7 batch 7: action risk, probability and branch summaries."""

import hashlib
import json
import unittest

import numpy as np

from neural.action_features import (
    ACTION_FEATURE_DIM_V7,
    ACTION_FEATURE_DIM_V7_BATCH6,
    ACTION_FEATURE_DIM_V7_BATCH7,
    ACTION_FEATURE_NAMES_V7,
    ACTION_FEATURE_NAMES_V7_BATCH6,
    ACTION_FEATURE_NAMES_V7_BATCH7,
    SLICE14_ACTION_RISK_FEATURE_NAMES,
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

_BATCH6_FP = "e3e39124cd24e3e27684306e3d401859083df65965e721eb3e5e8b89c48fcb4c"
_BATCH7_FP = "c03b2dd345f47dae0bffefc2a0d2b5731ee7d1eb8f2bf4cabc8d415d183149f5"


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


class Batch7SchemaIntegrityTest(unittest.TestCase):
    def test_schema_and_batch6_prefix_fingerprint(self):
        self.assertEqual(ACTION_FEATURE_DIM_V7_BATCH6, 452)
        self.assertEqual(ACTION_FEATURE_DIM_V7_BATCH7, 511)
        self.assertEqual(ACTION_FEATURE_DIM_V7, 552)
        self.assertEqual(len(SLICE14_ACTION_RISK_FEATURE_NAMES), 59)
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:452], ACTION_FEATURE_NAMES_V7_BATCH6)
        self.assertEqual(ACTION_FEATURE_NAMES_V7[:511], ACTION_FEATURE_NAMES_V7_BATCH7)
        self.assertEqual(_fp(ACTION_FEATURE_NAMES_V7_BATCH6), _BATCH6_FP)
        self.assertEqual(_fp(ACTION_FEATURE_NAMES_V7_BATCH7), _BATCH7_FP)

    def test_first_452_names_and_values_match_batch6(self):
        fixtures = (
            ("Surf", _private(), _tactical(), _impact()),
            ("Metronome", _private(), _tactical(), None),
            ("Population Bomb", _private(), _tactical(), None),
            ("Future Sight", _private(), _tactical(), None),
            ("Latias", _private(), _tactical(), None, "switch"),
        )
        for fixture in fixtures:
            move, private, tactical, impact, *maybe_kind = fixture
            kind = maybe_kind[0] if maybe_kind else "move"
            action = _action(move, kind)
            current = build_action_feature_vector_v7(action, private, tactical, impact)
            batch6 = np.concatenate(
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
            np.testing.assert_array_equal(current[:511], batch6, err_msg=move)


class AccuracyCritRiskTest(unittest.TestCase):
    def test_ordinary_damaging_move_has_sane_risk_fields(self):
        vec = _v7("Surf", impact=_impact(expected=0.25, hit=1.0))
        self.assertEqual(_val(vec, "hit_chance_known"), 1.0)
        self.assertEqual(_val(vec, "hit_chance"), 1.0)
        self.assertEqual(_val(vec, "miss_chance"), 0.0)
        self.assertEqual(_val(vec, "on_hit_damage_available"), 1.0)
        self.assertAlmostEqual(_val(vec, "expected_damage_includes_miss"), 0.25, places=5)
        self.assertEqual(_val(vec, "crit_chance_known"), 1.0)
        self.assertAlmostEqual(_val(vec, "crit_chance"), 1.0 / 24.0, places=5)
        self.assertEqual(_val(vec, "guaranteed_crit"), 0.0)
        for name in (
            "branch_pressure_present",
            "random_call_move",
            "multihit_distribution_known",
            "delayed_pressure_created",
            "residual_pressure_created",
        ):
            self.assertEqual(_val(vec, name), 0.0, name)

    def test_miss_adjusted_expected_damage_uses_hit_chance(self):
        vec = _v7("Hydro Pump", impact=_impact(expected=0.50, hit=0.80))
        self.assertAlmostEqual(_val(vec, "hit_chance"), 0.80, places=5)
        self.assertAlmostEqual(_val(vec, "miss_chance"), 0.20, places=5)
        self.assertAlmostEqual(_val(vec, "expected_damage_includes_miss"), 0.40, places=5)

    def test_guaranteed_crit_is_distinct_from_ordinary_crit(self):
        for move in ("Flower Trick", "Wicked Blow"):
            vec = _v7(move, impact=_impact(expected=0.40))
            self.assertEqual(_val(vec, "crit_chance_known"), 1.0)
            self.assertEqual(_val(vec, "crit_chance"), 1.0)
            self.assertEqual(_val(vec, "guaranteed_crit"), 1.0)


class BranchRiskTest(unittest.TestCase):
    def test_opponent_action_branch_moves_are_hidden_now(self):
        for move in ("Sucker Punch", "Thunderclap", "Focus Punch"):
            vec = _v7(move)
            self.assertEqual(_val(vec, "may_fail_due_to_opponent_action"), 1.0, move)
            self.assertEqual(_val(vec, "branch_pressure_present"), 1.0, move)
            self.assertEqual(_val(vec, "branch_condition_hidden_now"), 1.0, move)

    def test_active_turn_branch_moves_are_marked(self):
        for move in ("Fake Out", "First Impression"):
            vec = _v7(move)
            self.assertEqual(_val(vec, "may_fail_due_to_active_turn"), 1.0, move)
            self.assertEqual(_val(vec, "branch_pressure_present"), 1.0, move)

    def test_target_switch_and_history_power_branches_are_marked(self):
        payback = _v7("Payback")
        self.assertEqual(_val(payback, "may_fail_due_to_prior_turn_or_history"), 1.0)
        self.assertEqual(_val(payback, "power_boost_if_target_switches"), 1.0)
        pursuit = _v7("Pursuit")
        self.assertEqual(_val(pursuit, "may_fail_due_to_target_switch"), 1.0)
        self.assertEqual(_val(pursuit, "succeeds_if_target_switches"), 1.0)

    def test_feint_is_not_old_gen_protect_only_conditional(self):
        vec = _v7("Feint")
        self.assertEqual(_val(vec, "may_fail_due_to_opponent_action"), 0.0)
        self.assertEqual(_val(vec, "branch_pressure_present"), 0.0)


class RandomCallTest(unittest.TestCase):
    def test_metronome_has_known_format_pool_summary(self):
        vec = _v7("Metronome")
        self.assertEqual(_val(vec, "random_call_move"), 1.0)
        self.assertEqual(_val(vec, "callable_pool_known"), 1.0)
        self.assertGreater(_val(vec, "callable_count"), 100.0)
        self.assertGreater(_val(vec, "callable_damaging_count"), 0.0)
        self.assertEqual(_val(vec, "random_call_fail_closed"), 0.0)

    def test_sleep_talk_pool_uses_known_current_moves_without_sampling(self):
        private = _private()
        private["active_moves"] = [
            {"id": "surf", "name": "Surf"},
            {"id": "recover", "name": "Recover"},
            {"id": "sleeptalk", "name": "Sleep Talk"},
        ]
        vec = _v7("Sleep Talk", private=private)
        self.assertEqual(_val(vec, "random_call_move"), 1.0)
        self.assertEqual(_val(vec, "callable_pool_depends_on_sleep_state"), 1.0)
        self.assertEqual(_val(vec, "callable_pool_known"), 1.0)
        self.assertEqual(_val(vec, "callable_count"), 2.0)

    def test_copycat_and_assist_keep_provenance_gaps(self):
        copycat = _v7("Copycat")
        self.assertEqual(_val(copycat, "random_call_move"), 1.0)
        self.assertEqual(_val(copycat, "callable_pool_depends_on_last_move"), 1.0)
        self.assertEqual(_val(copycat, "random_call_fail_closed"), 1.0)
        assist = _v7("Assist")
        self.assertEqual(_val(assist, "callable_pool_depends_on_party"), 1.0)
        self.assertEqual(_val(assist, "callable_pool_depends_on_format_rules"), 1.0)


class MultiHitRiskTest(unittest.TestCase):
    def test_population_bomb_and_triple_axel_are_sequential(self):
        pop = _v7("Population Bomb")
        self.assertEqual(_val(pop, "multihit_distribution_known"), 1.0)
        self.assertEqual(_val(pop, "multihit_max"), 10.0)
        self.assertEqual(_val(pop, "sequential_accuracy_stops_on_miss"), 1.0)
        self.assertAlmostEqual(_val(pop, "per_hit_accuracy"), 0.90, places=5)
        triple = _v7("Triple Axel")
        self.assertEqual(_val(triple, "multihit_max"), 3.0)
        self.assertEqual(_val(triple, "per_hit_power_changes"), 1.0)

    def test_loaded_dice_and_skill_link_only_apply_when_state_supports_them(self):
        plain = _v7("Population Bomb")
        self.assertEqual(_val(plain, "loaded_dice_modified"), 0.0)
        loaded = _v7("Population Bomb", private=_private(item="Loaded Dice"))
        self.assertEqual(_val(loaded, "loaded_dice_modified"), 1.0)
        self.assertEqual(_val(loaded, "multihit_min"), 4.0)
        self.assertEqual(_val(loaded, "multihit_max"), 10.0)
        skill = _v7("Icicle Spear", private=_private(ability="Skill Link"))
        self.assertEqual(_val(skill, "skill_link_guaranteed"), 1.0)
        self.assertEqual(_val(skill, "multihit_min"), 5.0)
        self.assertEqual(_val(skill, "multihit_max"), 5.0)


class DelayedResidualPressureTest(unittest.TestCase):
    def test_future_moves_create_deferred_slot_pressure_not_damage(self):
        for move in ("Future Sight", "Doom Desire"):
            vec = _v7(move)
            self.assertEqual(_val(vec, "delayed_pressure_created"), 1.0, move)
            self.assertEqual(_val(vec, "delayed_turns_until_effect"), 2.0, move)
            self.assertEqual(_val(vec, "delayed_targets_opp_slot"), 1.0, move)
            self.assertEqual(_val(vec, "delayed_damage_deferred_to_rollout"), 1.0, move)
            self.assertEqual(_val(vec, "future_damage_unknown_now"), 1.0, move)

    def test_residual_and_binding_pressure_are_summarized(self):
        for move in ("Toxic", "Leech Seed", "Salt Cure"):
            vec = _v7(move)
            self.assertEqual(_val(vec, "residual_pressure_created"), 1.0, move)
            self.assertEqual(_val(vec, "residual_kind_known"), 1.0, move)
            self.assertEqual(_val(vec, "residual_source_known"), 1.0, move)
        bind = _v7("Bind")
        self.assertEqual(_val(bind, "binding_pressure_created"), 1.0)
        self.assertEqual(_val(bind, "residual_duration_known"), 0.0)


if __name__ == "__main__":
    unittest.main()
