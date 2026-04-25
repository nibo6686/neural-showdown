import unittest

from neural.import_showdown_logs import parse_showdown_log


class ShowdownLogImportTest(unittest.TestCase):
    def test_parse_small_public_log(self):
        summary = parse_showdown_log(
            [
                "|player|p1|Alice|",
                "|player|p2|Bob|",
                "|turn|1",
                "|switch|p1a: Pikachu|Pikachu, L80|100/100",
                "|move|p1a: Pikachu|Thunderbolt|p2a: Squirtle",
                "|win|Alice",
            ],
            source_path="sample.log",
        )
        self.assertEqual(summary["players"]["p1"], "Alice")
        self.assertEqual(summary["winner"], "Alice")
        self.assertEqual(summary["turns"], 1)
        self.assertEqual(summary["moves"][0]["move"], "Thunderbolt")
        self.assertFalse(summary["usable_for_training"])


if __name__ == "__main__":
    unittest.main()
