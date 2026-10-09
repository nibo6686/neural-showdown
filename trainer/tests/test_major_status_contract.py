"""CE-04F2 cross-runtime major-status protocol grammar controls."""

import unittest

from neural.protocol_contract import ProtocolRecordError, validate_protocol_record


class MajorStatusContractTest(unittest.TestCase):
    def test_source_shaped_major_status_records_match_the_typescript_boundary(self):
        accepted = (
            "|-status|p1a: Target|brn",
            "|-status|p2a: Target|slp|[from] move: Rest",
            "|-status|p1a: Target|tox|[from] item: Toxic Orb",
            "|-status|p2a: Target|par|[from] ability: Static|[of] p1a: Source",
            "|-status|p1a: Target|psn|[from] ability: Poison Touch|[of] p2a: Source",
            "|-status|p2a: Target|slp|[from] move: Sleep Powder",
            "|-status|p1a: Target|slp|[from] move: Hypnosis",
            "|-status|p2a: Target|slp|[from] move: Spore",
            "|-curestatus|p1a: Target|brn|[msg]",
            "|-curestatus|p2a: Target|tox|[from] ability: Natural Cure",
            "|-curestatus|p1a: Target|frz|[from] move: Scald",
            "|-curestatus|p2a: Target|frz|[from] move: Hydro Steam",
            "|-curestatus|p1a: Target|frz|[from] move: Matcha Gotcha",
            "|-curestatus|p2a: Target|frz|[from] move: Steam Eruption",
        )
        rejected = (
            "|-status|p1a: Target|fnt",
            "|-status|p1a: Target|brn|[from] item: Toxic Orb",
            "|-status|p1a: Target|par|[from] ability: Static|[of] p1a: Source",
            "|-curestatus|p1a: Target|brn",
            "|-curestatus|p1a: Target|frz|[from] move: Flamethrower",
            "|status|p1a: Target|brn|[msg]",
            "|status|p1a: Target|brn",
            "|curestatus|p2a: Target|tox",
            "|-status|p1a: Target|slp|[from] move: Yawn",
            "|-status|p1a: Target|psn|[from] ability: Poison Touch|[of] p1a: Source",
        )
        for record in accepted:
            with self.subTest(record=record):
                validate_protocol_record(record)
        for record in rejected:
            with self.subTest(record=record):
                with self.assertRaises(ProtocolRecordError):
                    validate_protocol_record(record)


if __name__ == "__main__":
    unittest.main()
