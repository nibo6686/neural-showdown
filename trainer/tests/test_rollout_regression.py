import json
import tempfile
import unittest
from pathlib import Path

from neural.sim_branch_evaluator import evaluate_actions


class RolloutRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        (self.tmpdir / "artifacts" / "regression").mkdir(parents=True, exist_ok=True)

    def _write_trace(self, name: str, protocol_log: list, turns: list):
        trace = {
            "replay_id": name,
            "format": "gen9randombattle",
            "protocol_log": protocol_log,
            "turns": turns,
        }
        path = self.tmpdir / f"{name}.json"
        path.write_text(json.dumps(trace), encoding="utf-8")
        return path

    def _run_case(self, name: str, payload: dict):
        step = payload["trace"]["turns"][0]["steps"][0]
        legal_actions = [action for action in step.get("legal_actions", []) if isinstance(action, dict)]
        results = evaluate_actions(
            payload,
            "p1",
            legal_actions,
            opponent_policy="uniform",
            rollout_config={"rollout_mode": "approximate", "rollouts_per_action": 4},
        )
        return results

    def test_regression_cases_report(self):
        cases = []

        # Case 1: Will-O-Wisp into already burned target
        proto1 = ["|turn|1", "|move|p1a: Morpeko|Will-O-Wisp|p2a: Opp", "|-status|p2a: Opp|brn"]
        steps1 = [
            {
                "step_index": 0,
                "p1_species": "Morpeko",
                "p1_hp_ratio": 1.0,
                "p2_species": "Opp",
                "p2_hp_ratio": 1.0,
                "legal_actions": [
                    {"index": 0, "kind": "move", "label": "move:Will-O-Wisp", "move": "Will-O-Wisp"},
                    {"index": 1, "kind": "move", "label": "move:Tackle", "move": "Tackle"},
                ],
                "chosen_action_index": 1,
                "protocol_log": proto1,
            }
        ]
        p1 = {"trace": {"protocol_log": proto1, "turns": [{"turn": 1, "steps": steps1}]}}
        res1 = self._run_case("will-o-wisp-burned", p1)
        cases.append(("will-o-wisp-burned", res1))

        # Case 2: Sleep Powder into immune target
        proto2 = ["|turn|1", "|move|p1a: Butterfree|Sleep Powder|p2a: Vileplume", "|-status|p2a: Vileplume|brn"]
        steps2 = [
            {
                "step_index": 0,
                "p1_species": "Butterfree",
                "p1_hp_ratio": 1.0,
                "p2_species": "Vileplume",
                "p2_hp_ratio": 1.0,
                "legal_actions": [
                    {"index": 0, "kind": "move", "label": "move:Sleep Powder", "move": "Sleep Powder"},
                    {"index": 1, "kind": "move", "label": "move:Giga Drain", "move": "Giga Drain"},
                ],
                "chosen_action_index": 1,
                "protocol_log": proto2,
            }
        ]
        p2 = {"trace": {"protocol_log": proto2, "turns": [{"turn": 1, "steps": steps2}]}}
        res2 = self._run_case("sleep-immune", p2)
        cases.append(("sleep-immune", res2))

        # Case 3: Swords Dance at +6
        proto3 = ["|turn|1", "|-boost|p1a: Dragapult|atk|6"]
        steps3 = [
            {
                "step_index": 0,
                "p1_species": "Dragapult",
                "p1_hp_ratio": 1.0,
                "p2_species": "Opp",
                "p2_hp_ratio": 1.0,
                "legal_actions": [
                    {"index": 0, "kind": "move", "label": "move:Swords Dance", "move": "Swords Dance"},
                    {"index": 1, "kind": "move", "label": "move:Tackle", "move": "Tackle"},
                ],
                "chosen_action_index": 1,
                "protocol_log": proto3,
            }
        ]
        p3 = {"trace": {"protocol_log": proto3, "turns": [{"turn": 1, "steps": steps3}]}}
        res3 = self._run_case("swords-dance-cap", p3)
        cases.append(("swords-dance-cap", res3))

        # Case 4: Type effectiveness sanity
        proto4 = ["|turn|1", "|move|p1a: Firemon|Flamethrower|p2a: Grassmon"]
        steps4 = [
            {
                "step_index": 0,
                "p1_species": "Firemon",
                "p1_hp_ratio": 1.0,
                "p2_species": "Grassmon",
                "p2_hp_ratio": 1.0,
                "legal_actions": [
                    {"index": 0, "kind": "move", "label": "move:Flamethrower", "move": "Flamethrower"},
                    {"index": 1, "kind": "move", "label": "move:Thunderbolt", "move": "Thunderbolt"},
                ],
                "chosen_action_index": 0,
                "protocol_log": proto4,
            }
        ]
        p4 = {"trace": {"protocol_log": proto4, "turns": [{"turn": 1, "steps": steps4}]}}
        res4 = self._run_case("type-effectiveness", p4)
        cases.append(("type-effectiveness", res4))

        # Case 5: Switch into obvious KO
        proto5 = ["|turn|1", "|move|p2a: Slowking|Surf|p1b: Coalossal", "|-damage|p1b: Coalossal|50/200"]
        steps5 = [
            {
                "step_index": 0,
                "p1_species": "Coalossal",
                "p1_hp_ratio": 1.0,
                "p2_species": "Slowking",
                "p2_hp_ratio": 1.0,
                "legal_actions": [
                    {"index": 8, "kind": "switch", "label": "switch:Coalossal"},
                    {"index": 0, "kind": "move", "label": "move:Tackle", "move": "Tackle"},
                ],
                "chosen_action_index": 0,
                "protocol_log": proto5,
            }
        ]
        p5 = {"trace": {"protocol_log": proto5, "turns": [{"turn": 1, "steps": steps5}]}}
        res5 = self._run_case("switch-into-ko", p5)
        cases.append(("switch-into-ko", res5))

        # Case 6: Ability-punished move (Defiant)
        proto6 = ["|turn|1", "|move|p1a: Leavanny|Lunge|p2a: Zapdos-Galar", "|-boost|p2a: Zapdos-Galar|atk|2"]
        steps6 = [
            {
                "step_index": 0,
                "p1_species": "Leavanny",
                "p1_hp_ratio": 1.0,
                "p2_species": "Zapdos-Galar",
                "p2_hp_ratio": 1.0,
                "legal_actions": [
                    {"index": 0, "kind": "move", "label": "move:Lunge", "move": "Lunge"},
                    {"index": 1, "kind": "move", "label": "move:U-turn", "move": "U-turn"},
                ],
                "chosen_action_index": 1,
                "protocol_log": proto6,
            }
        ]
        p6 = {"trace": {"protocol_log": proto6, "turns": [{"turn": 1, "steps": steps6}]}}
        res6 = self._run_case("ability-punish", p6)
        cases.append(("ability-punish", res6))

        # Case 7: Thunder Wave into already-paralyzed target (Wigglytuff vs Gouging Fire)
        proto7 = ["|turn|7", "|move|p1a: Wigglytuff|Thunder Wave|p2a: Gouging Fire", "|-status|p2a: Gouging Fire|par", "|turn|9", "|move|p1a: Wigglytuff|Thunder Wave|p2a: Gouging Fire", "|-fail|p2a: Gouging Fire|par"]
        steps7 = [{
            "step_index": 0,
            "turn": 9,
            "p1_species": "Wigglytuff",
            "p1_hp_ratio": 1.0,
            "p1_status": None,
            "p2_species": "Gouging Fire",
            "p2_hp_ratio": 1.0,
            "p2_status": "par",
            "legal_actions": [
                {"index": 0, "kind": "move", "label": "move:Thunder Wave", "move": "Thunder Wave"},
                {"index": 1, "kind": "move", "label": "move:Knock Off", "move": "Knock Off"},
                {"index": 2, "kind": "move", "label": "move:Alluring Voice", "move": "Alluring Voice"},
            ],
            "chosen_action_index": 1,
            "protocol_log": proto7,
        }]
        p7 = {"trace": {"protocol_log": proto7, "turns": [{"turn": 9, "steps": steps7}]}}
        res7 = self._run_case("thunder-wave-paralyzed", p7)
        cases.append(("thunder-wave-paralyzed", res7))

        # Build report
        report = {"cases": []}
        blocked_count = 0
        for name, results in cases:
            method_set = set([r.get("method") for r in results]) if results else set()
            rollout_available = any(m in {"approx_sim_rollout", "exact_sim_rollout"} for m in method_set)
            note = "rollout_unavailable" if not rollout_available else "approx_sim_rollout_available"
            verdict = "BLOCKED" if not rollout_available else "AVAILABLE"
            if not rollout_available:
                blocked_count += 1
            report["cases"].append({"name": name, "method_set": sorted(list(method_set)), "rollout_available": rollout_available, "verdict": verdict, "note": note})

        # Write report files
        out_json = Path("artifacts/regression/rollout_regression_report.json")
        out_md = Path("artifacts/regression/rollout_regression_report.md")
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

        md_lines = ["# Rollout Regression Report", ""]
        for item in report["cases"]:
            md_lines.append(f"- **{item['name']}**: verdict={item['verdict']}, rollout_available={item['rollout_available']}, methods={item['method_set']}")

        out_md.write_text("\n".join(md_lines), encoding="utf-8")

        # Assertions: report exists and all cases now have approximate rollout coverage.
        self.assertTrue(out_json.exists())
        self.assertTrue(out_md.exists())
        data = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertEqual(len(data["cases"]), 7)
        for entry in data["cases"]:
            self.assertTrue(entry["rollout_available"], msg=f"Expected approximate rollout for {entry['name']}")
        
        # Additional assertions for Thunder Wave regression
        thunder_wave_case = next((c for c in data["cases"] if c["name"] == "thunder-wave-paralyzed"), None)
        self.assertIsNotNone(thunder_wave_case, msg="Thunder Wave paralyzed case should be present")
        self.assertTrue(thunder_wave_case["rollout_available"], msg="Thunder Wave into paralyzed target should have approximate rollout")


if __name__ == "__main__":
    unittest.main()
