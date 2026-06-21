import json
import unittest
from pathlib import Path

from neural.vnext_labels import (
    chosen_action_label,
    is_magic_bounce_reflection,
    match_chosen_action,
    state_value_label,
)


class VNextLabelsTest(unittest.TestCase):
    def test_final_outcome_is_perspective_correct(self):
        self.assertEqual(state_value_label("p1", "p1"), 1.0)
        self.assertEqual(state_value_label("p1", "p2"), -1.0)
        self.assertIsNone(state_value_label("tie", "p1"))
        self.assertIsNone(state_value_label(None, "p1"))

    def test_move_and_switch_matching(self):
        actions = [
            {"kind": "move", "label": "move: Thunderbolt", "move": "Thunderbolt"},
            {"kind": "switch", "label": "switch: Garchomp"},
        ]
        self.assertEqual(match_chosen_action(actions, "move: Thunderbolt"), 0)
        self.assertEqual(match_chosen_action(actions, "switch: Garchomp"), 1)
        self.assertIsNone(match_chosen_action(actions, "move: Surf"))

    def test_showdown_style_move_id_normalization(self):
        actions = [{"kind": "move", "label": "move: Will-O-Wisp", "move": "Will-O-Wisp"}]
        self.assertEqual(match_chosen_action(actions, "move: Will O Wisp"), 0)

    def test_forced_switch_uses_same_provable_species_match(self):
        actions = [{"kind": "switch", "label": "switch: Ho-Oh"}]
        self.assertEqual(match_chosen_action(actions, "switch: Ho Oh"), 0)

    def test_tera_move_matching_uses_turn_tera_event(self):
        move = {"type": "move", "side": "p1", "move": "Tera Blast"}
        events = [{"type": "tera", "side": "p1", "tera_type": "Ghost"}, move]
        label = chosen_action_label(move, turn_events=events)
        self.assertEqual(label, "move_tera: Tera Blast")
        actions = [
            {"kind": "move", "label": "move: Tera Blast", "move": "Tera Blast"},
            {"kind": "move_tera", "label": "move_tera: Tera Blast", "move": "Tera Blast"},
        ]
        self.assertEqual(match_chosen_action(actions, label), 1)

    def test_non_decision_and_unmatched_generate_no_positive(self):
        self.assertIsNone(chosen_action_label({"type": "wait"}, turn_events=[]))
        actions = [{"kind": "move", "label": "move: Surf", "move": "Surf"}]
        chosen = match_chosen_action(actions, "move: Thunderbolt")
        labels = [1 if index == chosen else 0 for index in range(len(actions))]
        self.assertIsNone(chosen)
        self.assertEqual(sum(labels), 0)

    def test_magic_bounce_reflection_is_not_an_actor_choice(self):
        event = {
            "type": "move",
            "side": "p2",
            "move": "Will-O-Wisp",
            "raw": (
                "|move|p2a: Hatterene|Will-O-Wisp|p1a: Misdreavus|"
                "[from] ability: Magic Bounce"
            ),
        }
        self.assertTrue(is_magic_bounce_reflection(event))
        self.assertIsNone(chosen_action_label(event, turn_events=[event]))

    def test_label_manifest_is_valid_json(self):
        path = Path("artifacts/training_plan/vnext_label_manifest.json")
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["label_version"], "vnext-diagnostic-labels-v1")


if __name__ == "__main__":
    unittest.main()
