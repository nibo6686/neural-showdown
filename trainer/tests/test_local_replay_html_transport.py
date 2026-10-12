"""Independent saved-HTML transport oracles; no replay fidelity assertion."""

from contextlib import ExitStack
import hashlib
import html
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from neural import compare_action_rankers as loader
from neural import compare_replay_evals as replay_eval
from neural import build_live_private_value_dataset as private_dataset
from neural import build_replay_value_dataset as public_dataset
from neural.parse_replay_logs import parse_hp_fraction, parse_protocol_log

FIXTURES = Path(__file__).parent / "fixtures/perspective-replay"
FILES = [
    ("Gen9RandomBattle-2026-10-10-hasklne-kaiserme.html", "gen9randombattle", 370, "kaiser_me", "dcdb4065f50d6e0763f077e194564d138458959682d0deea25e03fb1e83e7b42"),
    ("Gen9OU-2026-10-10-hasklne-loob.html", "gen9ou", 305, "loob", "c44a0b666b492ebcca9bd200f00b1628daf3f9472c236fb3a36f5947ba94d18f"),
]
# Source-index, side, literal decoded condition, fraction, status: independent raw/rendered inspection.
HP = {
    "gen9randombattle": [(18, "p1", "310/310", 1, None), (27, "p1", "163/310", 163/310, None), (149, "p1", "99/216", 99/216, None),
                           (19, "p2", "362/362", 1, None), (28, "p2", "313/362", 313/362, None), (30, "p2", "335/362", 335/362, None),
                           (41, "p1", "0 fnt", 0, None), (54, "p2", "0 fnt", 0, None)],
    "gen9ou": [(38, "p1", "100/100", 1, None), (86, "p1", "66/100", .66, None), (211, "p1", "81/100", .81, None),
                 (39, "p2", "100/100", 1, None), (47, "p2", "32/100", .32, None), (124, "p2", "74/100 tox", .74, "tox"),
                 (134, "p2", "86/100 tox", .86, "tox"), (185, "p2", "86/100 tox", .86, "tox"), (190, "p2", "99/100 tox", .99, "tox"),
                 (202, "p2", "100/100 tox", 1, "tox"), (235, "p2", "0 fnt", 0, None), (291, "p2", "0 fnt", 0, None)],
}


def source_records(path):
    block = re.search(r'<script type="text/plain" class="battle-log-data">(.*?)</script>', path.read_text(encoding="utf-8"), re.S).group(1)
    return [line.removesuffix("\r") for line in block.split("\n") if line.startswith("|")]


class LocalReplayHTMLTransportTest(unittest.TestCase):
    def setUp(self):
        guards = ExitStack()
        self.addCleanup(guards.close)
        for target, name in [(loader, "load_replay_trajectory"), (loader, "_load_ranker"), (loader, "torch_load"), (loader, "_score_with_ranker"),
                             (loader, "ActionRankerMLP"), (loader.torch, "load"), (replay_eval.urllib.request, "urlopen"),
                             (private_dataset, "build_live_private_value_dataset"), (public_dataset, "build_public_replay_value_dataset")]:
            guards.enter_context(patch.object(target, name, side_effect=AssertionError(f"forbidden local-import side effect: {name}")))

    def load(self, path, fmt="gen9randombattle"):
        return loader._load_replay(str(path), replay_dir=path.parent, trajectories_path=path.parent / "unused", format_name=fmt)

    def local_html(self, text, suffix=".html"):
        directory = tempfile.TemporaryDirectory(prefix="neural-html-transport-")
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / ("replay" + suffix)
        path.write_bytes(text.encode("utf-8"))
        return path

    def test_supplied_fixtures_literal_hp_and_index_mapping(self):
        evidence = []
        for filename, fmt, count, opponent, digest in FILES:
            with self.subTest(fixture=filename):
                path = FIXTURES / filename
                before_bytes = path.read_bytes()
                self.assertEqual(hashlib.sha256(before_bytes).hexdigest(), digest)
                raw = source_records(path)
                expected = [html.unescape(record.replace("\\/", "/")) for record in raw]
                trajectory = self.load(path, fmt)
                self.assertEqual(trajectory, self.load(path, fmt))
                self.assertEqual(trajectory["protocol_log"], expected)
                self.assertEqual(len(expected), count)
                self.assertEqual(trajectory["players"], {"p1": "hasklne", "p2": opponent})
                self.assertEqual(trajectory["turns"][0]["turn"], 0)
                self.assertEqual(trajectory["winner_side"], "p1")
                self.assertEqual(trajectory["winner"], "hasklne")
                self.assertEqual(expected[:2], raw[:2])
                self.assertEqual(expected[8], "|rated|")
                events = [event for turn in trajectory["turns"] for event in turn["events"]]
                for index, side, condition, fraction, status in HP[fmt]:
                    event = next(event for event in events if event["raw"] == expected[index])
                    self.assertEqual(event["side"], side)
                    self.assertEqual(event["condition"], condition)
                    self.assertEqual(event["hp_fraction"], fraction)
                    self.assertEqual(event["status"], status)
                    evidence.append({"fixture": filename, "index": index, "cursor": index+1, "source": raw[index], "imported": expected[index], "side": side, "expected_condition": condition, "expected_ratio": fraction, "actual_ratio": event["hp_fraction"], "status": status})
                self.assertEqual(path.read_bytes(), before_bytes)
                evidence.append({"fixture": filename, "sha256": digest, "record_count": count, "mapping": [{"index": i, "original": record, "imported": expected[i]} for i, record in enumerate(raw)], "scope": "diagnostic only" if fmt == "gen9ou" else "supported format"})
        output = os.environ.get("LOCAL_REPLAY_HTML_REPORT")
        if output:
            Path(output).write_text(json.dumps({"source_authenticity": "unverified", "evidence": evidence}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

    def test_literal_transport_controls_and_outside_lookalikes(self):
        source = r'''|j|☆Pokémon
|rated|
|switch|p1a: Pokémon|Pikachu|25\/100
|-damage|p1a: Pokémon|20/100 brn
|-heal|p1a: Pokémon|50\/100 brn
|-damage|p1a: Pokémon|0 fnt
|
|raw|Ω 😀 &amp; &lt;\/strong&gt; |win|inert &amp;lt; \n \u0041 \t
|raw|entity-escape &#92;/ stays transport text
|raw|duplicate
|raw|duplicate
|win|Pokémon'''
        expected = ["|j|☆Pokémon", "|rated|", "|switch|p1a: Pokémon|Pikachu|25/100", "|-damage|p1a: Pokémon|20/100 brn", "|-heal|p1a: Pokémon|50/100 brn", "|-damage|p1a: Pokémon|0 fnt", "|",
                    r'|raw|Ω 😀 & </strong> |win|inert &lt; \n \u0041 \t', r'|raw|entity-escape \/ stays transport text', "|raw|duplicate", "|raw|duplicate", "|win|Pokémon"]
        text = '|win|outside-before\n&lt;script type="text/plain" class="battle-log-data"&gt;\n|win|encoded-outside\n&lt;/script&gt;\n<script type="text/plain" class="battle-log-data">\n'+source+'\n</script>\n|win|outside-after'
        path = self.local_html(text, ".htm")
        trajectory = self.load(path)
        self.assertEqual(trajectory["protocol_log"], expected)
        self.assertEqual(trajectory["winner"], "Pokémon")
        hp = [event for turn in trajectory["turns"] for event in turn["events"] if "hp_fraction" in event]
        self.assertEqual([event["hp_fraction"] for event in hp], [.25, .20, .50, 0])
        self.assertEqual([event["status"] for event in hp], [None, "brn", "brn", None])
        self.assertEqual(path.read_bytes(), text.encode("utf-8"))

    def test_encoded_script_markup_is_inert_inside_one_record(self):
        text = '<script type="text/plain" class="battle-log-data">\n|raw|&lt;/script&gt;&lt;script class=&quot;battle-log-data&quot;&gt;|win|inert\n|win|real\n</script>'
        self.assertEqual(self.load(self.local_html(text))["protocol_log"], ['|raw|</script><script class="battle-log-data">|win|inert', '|win|real'])

    def test_missing_ambiguous_empty_and_malformed_blocks_fail_locally(self):
        block = '<script type="text/plain" class="battle-log-data">\n|win|real\n</script>'
        for text in ['|win|outside', '&lt;script type="text/plain" class="battle-log-data"&gt;\n|win|outside\n&lt;/script&gt;', block+block,
                     block.replace('</script>', ''), '<script type="text/plain" class="battle-log-data"></script>', block.replace('text/plain', 'text/javascript'),
                     block.replace('class="battle-log-data"', 'class="battle-log-data" class="other"')]:
            with self.subTest(text=text):
                with self.assertRaisesRegex(ValueError, 'saved HTML replay'):
                    self.load(self.local_html(text))

    def test_entity_record_controls_cannot_inject_commands(self):
        for entity in ['&#10;', '&#13;', '&#11;', '&#12;', '&#0;', '&#x85;', '&#x2028;', '&#x2029;']:
            with self.subTest(entity=entity):
                text = '<script type="text/plain" class="battle-log-data">\n|raw|inert'+entity+'|win|injected\n|win|real\n</script>'
                with self.assertRaisesRegex(ValueError, 'saved HTML replay'):
                    self.load(self.local_html(text))

    def test_encoded_record_start_cannot_be_promoted_to_command(self):
        text = '<script type="text/plain" class="battle-log-data">\n&#124;win|injected\n|win|real\n</script>'
        self.assertEqual(self.load(self.local_html(text))["protocol_log"], ['|win|real'])

    def test_encoded_command_tokens_cannot_be_promoted_to_commands(self):
        for record in ['|&#119;in|injected', '|wi&#110;|injected', '|win&#124;injected', '|win&vert;injected', '|&VerticalLine;win|injected']:
            with self.subTest(record=record):
                text = '<script type="text/plain" class="battle-log-data">\n'+record+'\n|win|real\n</script>'
                with self.assertRaisesRegex(ValueError, 'saved HTML replay'):
                    self.load(self.local_html(text))

    def test_non_html_routes_and_generic_parser_do_not_decode_transport(self):
        source = [r'|switch|p1a: A|Pikachu|25\/100', r'|-damage|p1a: A|20\x2f100', '|win|real']
        for suffix in ['.log', '.json']:
            with self.subTest(suffix=suffix):
                path = self.local_html('\n'.join(source) if suffix == '.log' else json.dumps({'log': source}), suffix)
                with patch.object(loader, 'load_replay_trajectory', wraps=replay_eval.load_replay_trajectory) as route:
                    trajectory = self.load(path)
                route.assert_called_once()
                self.assertEqual(trajectory['protocol_log'], source)
                self.assertIsNone(trajectory['turns'][0]['events'][0]['hp_fraction'])
                self.assertIsNone(trajectory['turns'][0]['events'][1]['hp_fraction'])
        self.assertIsNone(parse_hp_fraction(r'25\/100'))
        self.assertIsNone(parse_hp_fraction(r'20\x2f100'))
        self.assertEqual(parse_protocol_log(source)['protocol_log'], source)
        html_path = self.local_html('<script type="text/plain" class="battle-log-data">\n|-damage|p1a: A|20\\x2f100\n</script>')
        self.assertIsNone(self.load(html_path)['turns'][0]['events'][0]['hp_fraction'])


if __name__ == '__main__':
    unittest.main()
