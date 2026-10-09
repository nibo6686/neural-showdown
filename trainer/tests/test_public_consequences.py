import copy
import unittest

from neural.public_health import project_public_health, validate_public_health
from neural.public_ability import public_gas_sources, validate_public_ability


class PublicConsequenceTests(unittest.TestCase):
    def test_partial_terminal_authority_replays_only_supplied_ability_fields(self):
        for actor, other in (("p1", "p2"), ("p2", "p1")):
            for fields, suffix, expected in (
                (dict(ability=None, base_ability="imposter"), [f"|-transform|{actor}a: Own|{other}a: Target", f"|faint|{actor}a: Own"], dict(ability="imposter", base_ability="imposter")),
                (dict(ability="static", base_ability=None), [f"|-transform|{actor}a: Own|{other}a: Target", f"|-ability|{actor}a: Own|Air Lock"], dict(ability="airlock", base_ability=None)),
                (dict(ability=None, base_ability="terashift"), [f"|detailschange|{actor}a: Own|Terapagos-Stellar"], dict(ability=None, base_ability=None)),
            ):
                prefix = [f"|switch|{actor}a: Own|Ditto|100/100"]
                row = dict(ident=f"{actor}: Own", active=False, fainted=True, transformed=False, item=None,
                           ability_suppressed=False, ability_state="known" if expected["ability"] else "unknown", **expected)
                predecessor = dict(schema_version="observable-battle-state/v2", battle_id="partial", perspective=actor,
                                   protocol_prefix=prefix, request={"side": [dict(ident=f"{actor}: Own", active=True, item=None, **fields)]}, view={"self_team": [row]})
                observation = dict(schema_version="observable-battle-state/v2", battle_id="partial", perspective=actor,
                                   protocol_prefix=prefix + suffix, request=None, view=dict(terminated=True, self_team=[copy.deepcopy(row)], opponent_team=[]))
                validate_public_ability(observation, predecessor)
                for field in ("ability", "base_ability", "ability_state"):
                    bad = copy.deepcopy(observation); bad["view"]["self_team"][0][field] = "none" if field == "ability_state" else "levitate"
                    unchanged = copy.deepcopy(bad)
                    with self.assertRaisesRegex(ValueError, "Public ability evidence mismatch"): validate_public_ability(bad, predecessor)
                    self.assertEqual(bad, unchanged)

    def test_requestless_invalidation_requires_independent_current_and_base_authority(self):
        for actor, other in (("p1", "p2"), ("p2", "p1")):
            start = [f"|switch|{actor}a: Own|Ditto|100/100"]
            transform = start + [f"|-transform|{actor}a: Own|{other}a: Target"]
            unknown = dict(ident=f"{actor}: Own", ability=None, base_ability=None, ability_state="unknown",
                           ability_suppressed=False, active=True, fainted=False, transformed=True, item=None)
            for command in ("-transform", "detailschange", "-formechange"):
                prefix = transform if command == "-transform" else start + [f"|{command}|{actor}a: Own|Terapagos-Stellar"]
                observation = dict(perspective=actor, protocol_prefix=prefix, request=None,
                                   view=dict(self_team=[copy.deepcopy(unknown)], opponent_team=[]))
                validate_public_ability(observation)
                for owner in (None, {"side": []}, {"side": [{"ident": f"{actor}: Own"}]},
                              {"side": [{"ident": f"{actor}: Own", "base_ability": "imposter"}]}):
                    for field, value in (("ability", "levitate"), ("base_ability", "levitate"),
                                         ("ability_state", "known"), ("ability_suppressed", True)):
                        bad = copy.deepcopy(observation); bad["request"] = owner
                        if owner and owner["side"] and owner["side"][0].get("base_ability"):
                            bad["view"]["self_team"][0]["base_ability"] = "imposter"
                        bad["view"]["self_team"][0][field] = value
                        unchanged = copy.deepcopy(bad)
                        with self.assertRaisesRegex(ValueError, "Public ability evidence mismatch"): validate_public_ability(bad)
                        self.assertEqual(bad, unchanged)
                supplied = copy.deepcopy(observation)
                supplied["request"] = {"side": [{"ident": f"{actor}: Own", "ability": "static", "base_ability": "imposter", "item": None}]}
                supplied["view"]["self_team"][0].update(ability="static", base_ability="imposter", ability_state="known")
                validate_public_ability(supplied)
            for suffix in ([f"|-ability|{actor}a: Own|Air Lock"],
                           [f"|-ability|{actor}a: Own|Static|[from] ability: Trace|[of] {other}a: Target",
                            f"|-ability|{actor}a: Own|Air Lock"]):
                observation = dict(perspective=actor, protocol_prefix=transform + suffix, request=None,
                                   view=dict(self_team=[{**unknown, "ability": "airlock", "ability_state": "known"}], opponent_team=[]))
                validate_public_ability(observation)
                observation["view"]["self_team"][0]["base_ability"] = "airlock"
                with self.assertRaisesRegex(ValueError, "Public ability evidence mismatch"): validate_public_ability(observation)
            for species, ability in (("Terapagos-Stellar", "Teraform Zero"), ("Ogerpon-Teal-Tera", "Embody Aspect (Teal)"),
                                     ("Ogerpon-Wellspring-Tera", "Embody Aspect (Wellspring)"), ("Ogerpon-Hearthflame-Tera", "Embody Aspect (Hearthflame)"),
                                     ("Ogerpon-Cornerstone-Tera", "Embody Aspect (Cornerstone)")):
                name = ability.lower().replace(" ", "").replace("(", "").replace(")", "")
                prefix = start + [f"|detailschange|{actor}a: Own|{species}", f"|-ability|{actor}a: Own|{ability}" + ("|boost" if ability.startswith("Embody") else "")]
                observation = dict(perspective=actor, protocol_prefix=prefix, request=None,
                                   view=dict(self_team=[{**unknown, "ability": name, "base_ability": name, "ability_state": "known", "transformed": False}], opponent_team=[]))
                validate_public_ability(observation)
                observation["view"]["self_team"][0]["base_ability"] = "levitate"
                with self.assertRaisesRegex(ValueError, "Public ability evidence mismatch"): validate_public_ability(observation)

    def test_trace_requestless_copy_requires_public_name_and_representable_state(self):
        for actor, other in (("p1", "p2"), ("p2", "p1")):
            prefix = [f"|switch|{actor}a: Gardevoir|Gardevoir, L83|100/100",
                      f"|-ability|{actor}a: Gardevoir|Static|[from] ability: Trace|[of] {other}a: Pikachu"]
            row = dict(ident=f"{actor}: Gardevoir", ability="static", ability_state="changed",
                       ability_suppressed=False, active=True, fainted=False, transformed=False, item=None)
            observation = dict(perspective=actor, protocol_prefix=prefix, request=None,
                               view=dict(self_team=[row], opponent_team=[]))
            validate_public_ability(observation)
            partial = copy.deepcopy(observation); partial["request"] = {"side": [{"ident": f"{actor}: Gardevoir"}]}
            validate_public_ability(partial)
            cached = copy.deepcopy(observation); cached["view"]["self_team"][0]["ability_state"] = "known"
            validate_public_ability(cached)
            for field, value in (("ability", None), ("ability", "levitate"), ("ability_state", "unknown"),
                                 ("ability_state", "none"), ("ability_state", "suppressed")):
                bad = copy.deepcopy(observation); bad["view"]["self_team"][0][field] = value
                unchanged = copy.deepcopy(bad)
                with self.assertRaisesRegex(ValueError, "Public ability"):
                    validate_public_ability(bad)
                self.assertEqual(bad, unchanged)
            for field in ("ability", "ability_state", "ability_suppressed"):
                bad = copy.deepcopy(observation); del bad["view"]["self_team"][0][field]
                with self.assertRaisesRegex(ValueError, "Public ability"):
                    validate_public_ability(bad)
            for view in ({}, {"self_team": []}, {"self_team": [], "opponent_team": [row]}):
                with self.assertRaisesRegex(ValueError, "exactly one"):
                    validate_public_ability({**observation, "view": view})
            for cleanup in (f"|switch|{actor}a: Bench|Eevee|100/100", f"|drag|{actor}a: Bench|Eevee|100/100", f"|faint|{actor}a: Gardevoir"):
                cleared = copy.deepcopy(observation); cleared["protocol_prefix"].append(cleanup)
                cleared["view"]["self_team"][0].update(ability=None, ability_state="unknown", active=False)
                validate_public_ability(cleared)
                cleared["view"]["self_team"][0].update(ability="static", ability_state="changed")
                with self.assertRaisesRegex(ValueError, "Public ability"):
                    validate_public_ability(cleared)

    def test_plain_boost_requestless_reveal_requires_name_state_and_cleanup(self):
        for actor in ("p1", "p2"):
            for ability, suffix in (("Air Lock", ""), ("Intimidate", "|boost")):
                name = ability.lower().replace(" ", "")
                prefix = [f"|switch|{actor}a: Source|Rayquaza|100/100",
                          f"|-ability|{actor}a: Source|{ability}{suffix}"]
                row = dict(ident=f"{actor}: Source", ability=name, base_ability=name, ability_state="known",
                           ability_suppressed=False, active=True, fainted=False, transformed=False, item=None)
                observation = dict(perspective=actor, protocol_prefix=prefix, request=None,
                                   view=dict(self_team=[row], opponent_team=[]))
                validate_public_ability(observation)
                for field, value in (("ability", None), ("ability", "static"), ("ability_state", "unknown"),
                                     ("ability_state", "none"), ("ability_suppressed", True)):
                    bad = copy.deepcopy(observation); bad["view"]["self_team"][0][field] = value
                    unchanged = copy.deepcopy(bad)
                    with self.assertRaisesRegex(ValueError, "Public ability"): validate_public_ability(bad)
                    self.assertEqual(bad, unchanged)
                for field in ("ability", "ability_state", "ability_suppressed"):
                    bad = copy.deepcopy(observation); del bad["view"]["self_team"][0][field]
                    with self.assertRaisesRegex(ValueError, "Public ability"): validate_public_ability(bad)
                for cleanup in (f"|switch|{actor}a: Bench|Eevee|100/100", f"|drag|{actor}a: Bench|Eevee|100/100", f"|faint|{actor}a: Source"):
                    cleared = copy.deepcopy(observation)
                    cleared["protocol_prefix"].extend([f"|-ability|{actor}a: Source|Pressure", cleanup])
                    cleared["view"]["self_team"][0]["active"] = False
                    validate_public_ability(cleared)
                    cleared["view"]["self_team"][0]["ability"] = "pressure"
                    with self.assertRaisesRegex(ValueError, "Public ability"): validate_public_ability(cleared)

    def test_every_health_writer_and_last_writer_requires_complete_correctly_sided_fields(self):
        writers = [
            ["|-damage|p1a: One|42/100 brn"],
            ["|-heal|p1a: One|86/100"],
            ["|-sethp|p1a: One|50/100|[from] move: Pain Split"],
            ["|-status|p1a: One|par"],
            ["|-status|p1a: One|brn", "|-curestatus|p1a: One|brn"],
            ["|-status|p1a: One|brn", "|-damage|p1a: One|0 fnt", "|faint|p1a: One"],
            ["|-damage|p1a: One|42/100 brn", "|-heal|p1a: One|100/100"],
            ["|drag|p1a: Two|Eevee, L80|76/100 par"],
            ["|replace|p1a: Actual|Zoroark, L80|100/100"],
            ["|-heal|p1a: One|100/100|[from] move: Wish|[wisher] Source"],
            ["|-status|p1a: One|brn", "|-heal|p1a: One|100/100|[from] move: Healing Wish"],
            ["|-damage|p1a: One|0 fnt", "|faint|p1a: One", "|-heal|p1: One|50/100|[from] move: Revival Blessing"],
        ]
        for suffix in writers:
            prefix = ["|switch|p1a: One|Snorlax, L80|100/100"] + suffix
            rows = [{"ident": ident, **facts} for ident, facts in project_public_health(prefix).items()]
            observation = {"perspective": "p1", "protocol_prefix": prefix, "request": None,
                           "view": {"self_team": rows, "opponent_team": []}}
            validate_public_health(observation)
            for index, row in enumerate(rows):
                for key in ("hp_text", "hp_ratio", "status", "fainted", "active"):
                    if key not in row:
                        continue
                    bad = copy.deepcopy(observation)
                    del bad["view"]["self_team"][index][key]
                    with self.subTest(suffix=suffix, key=key), self.assertRaisesRegex(ValueError, "Public health"):
                        validate_public_health(bad)
            for bad_view in ({}, {"self_team": [], "opponent_team": rows}):
                with self.assertRaisesRegex(ValueError, "exactly one"):
                    validate_public_health({**observation, "view": bad_view})

    def test_owned_exact_hp_matches_public_bucket_without_disclosing_exact_opponent_hp(self):
        prefix = ["|switch|p1a: One|Snorlax, L80|99/100"]
        owner = {"ident": "p1: One", "condition": "999/1000", "active": True}
        row = {"ident": "p1: One", "hp_text": "999/1000", "hp_ratio": .999, "status": None, "fainted": False, "active": True}
        observation = {"perspective": "p1", "protocol_prefix": prefix, "request": {"side": [owner]},
                       "view": {"self_team": [row], "opponent_team": []}}
        validate_public_health(observation)
        bad = copy.deepcopy(observation); bad["view"]["self_team"][0]["hp_text"] = "99/100"
        with self.assertRaisesRegex(ValueError, "owner request"):
            validate_public_health(bad)
        opponent = {"perspective": "p2", "protocol_prefix": prefix, "request": None,
                    "view": {"self_team": [], "opponent_team": [{"ident": "p1: One", **project_public_health(prefix)["p1: One"]}]}}
        validate_public_health(opponent)
        opponent["view"]["opponent_team"][0].update(hp_text="999/1000", hp_ratio=.999)
        with self.assertRaisesRegex(ValueError, "public prefix"):
            validate_public_health(opponent)

    def test_owned_illusion_appearance_binds_only_addressed_owner_active_identity(self):
        prefix = ["|switch|p1a: Disguise|Snorlax, L80|100/100", "|-damage|p1a: Disguise|50/100"]
        owner = {"ident": "p1: Actual", "condition": "100/200", "active": True, "ability": "illusion"}
        bench = {"ident": "p1: Disguise", "condition": "200/200", "active": False}
        rows = [{"ident": owner["ident"], "hp_text": "100/200", "hp_ratio": .5, "status": None, "fainted": False, "active": True},
                {"ident": bench["ident"], "hp_text": "200/200", "hp_ratio": 1, "status": None, "fainted": False, "active": False}]
        observation = {"perspective": "p1", "protocol_prefix": prefix, "request": {"side": [owner, bench]},
                       "view": {"self_team": rows, "opponent_team": []}}
        validate_public_health(observation)
        for ability in (None, "immunity"):
            candidate = copy.deepcopy(observation)
            if ability is None:
                del candidate["request"]["side"][0]["ability"]
            else:
                candidate["request"]["side"][0]["ability"] = ability
            unchanged = copy.deepcopy(candidate)
            with self.assertRaisesRegex(ValueError, "legitimate Illusion roster authority"):
                validate_public_health(candidate)
            self.assertEqual(candidate, unchanged)
        rows[0]["hp_ratio"] = 1
        with self.assertRaisesRegex(ValueError, "owner request"):
            validate_public_health(observation)

    def test_gas_sources_and_owned_name_suppression_partial_false_matrix(self):
        prefix = ["|switch|p1a: Gas|Weezing, L80|100/100", "|-ability|p1a: Gas|Neutralizing Gas",
                  "|switch|p2a: Foe|Arcanine, L80|100/100", "|-ability|p2a: Foe|Intimidate"]
        self.assertEqual(public_gas_sources(prefix), {"p1: Gas"})
        self.assertEqual(public_gas_sources(prefix + ["|faint|p1a: Gas"]), set())
        owner = {"ident": "p2: Foe", "ability": "intimidate", "item": None}
        row = {"ident": "p2: Foe", "ability": "intimidate", "ability_state": "suppressed", "ability_suppressed": True,
               "item": None, "active": True, "fainted": False, "transformed": False}
        observation = {"protocol_prefix": prefix, "view": {"self_team": [row]}, "request": {"side": [owner]}}
        validate_public_ability(observation)
        for field in ("ability", "ability_suppressed"):
            bad = copy.deepcopy(observation); del bad["view"]["self_team"][0][field]
            with self.assertRaisesRegex(ValueError, "Public ability"):
                validate_public_ability(bad)
        for field, false in (("ability", "levitate"), ("ability_suppressed", False), ("item", "abilityshield")):
            bad = copy.deepcopy(observation); bad["view"]["self_team"][0][field] = false
            with self.assertRaisesRegex(ValueError, "Public ability"):
                validate_public_ability(bad)
        owner["item"] = row["item"] = "abilityshield"
        row["ability_suppressed"] = False; row["ability_state"] = "known"
        validate_public_ability(observation)
        owner["ability"] = row["ability"] = "iceface"
        owner["item"] = row["item"] = None
        validate_public_ability(observation)


class PublicItemConsequenceTests(unittest.TestCase):
    def test_ordered_item_writer_presence_absence_unknown_and_omissions(self):
        from neural.public_item import project_public_items, project_public_item_dispositions, validate_public_items
        writers = [
            ["|-item|p1a: One|Air Balloon"],
            ["|-item|p1a: One|Leftovers|[from] ability: Frisk|[of] p2a: Other"],
            ["|-enditem|p1a: One|Sitrus Berry|[eat]", "|-heal|p1a: One|67/100|[from] item: Sitrus Berry"],
            ["|-enditem|p1a: One|Air Balloon"],
            ["|-enditem|p1a: One|White Herb"],
            ["|-enditem|p1a: One|Leftovers|[from] move: Knock Off|[of] p2a: Other"],
            ["|-enditem|p1a: One|White Herb", "|-item|p1a: One|White Herb|[from] move: Recycle"],
            ["|-item|p1a: One|Leftovers|[from] move: Trick", "|-enditem|p1a: One|Leftovers|[silent]|[from] move: Trick"],
            ["|-enditem|p1a: One|Leftovers|[silent]|[from] move: Switcheroo", "|-item|p1a: One|Choice Scarf|[from] move: Switcheroo"],
            ["|item|p1a: One|Leftovers", "|enditem|p1a: One|Leftovers"],
            ["|-enditem|p1a: One|Sitrus Berry|[eat]", "|replace|p1a: Actual|Zoroark, L80|67/100"],
            ["|-item|p1a: One|Air Balloon", "|faint|p1a: One"],
            ["|-item|p1a: One|Air Balloon", "|switch|p1a: One|Snorlax, L80|100/100"],
        ]
        for suffix in writers:
            prefix = ["|switch|p1a: One|Snorlax, L80|100/100"] + suffix
            facts = project_public_items(prefix)
            for perspective in ("p1", "p2"):
                team = "self_team" if perspective == "p1" else "opponent_team"
                rows = []
                for target, item in facts.items():
                    row = {"ident": target}
                    if team == "self_team": row.update(item=item, item_suppressed=False, **project_public_item_dispositions(prefix)[target])
                    elif item is not None: row["item"] = "has-item"
                    rows.append(row)
                observation = {"perspective": perspective, "request": None, "protocol_prefix": prefix,
                               "view": {"self_team": [], "opponent_team": [], team: rows}}
                validate_public_items(observation)
                for index, row in enumerate(rows):
                    bad = copy.deepcopy(observation)
                    if team == "self_team": bad["view"][team][index]["item"] = None if row.get("item") else "leftovers"
                    elif row.get("item"): del bad["view"][team][index]["item"]
                    else: bad["view"][team][index]["item"] = "has-item"
                    with self.subTest(prefix=prefix, perspective=perspective), self.assertRaisesRegex(ValueError, "Public item"):
                        validate_public_items(bad)
                if facts:
                    for view in ({}, {team: False}, {team: [{}]}):
                        with self.assertRaisesRegex(ValueError, "Public item"):
                            validate_public_items({**observation, "view": view})
        validate_public_items({"perspective": "p2", "protocol_prefix": [], "view": {}})
        with self.assertRaisesRegex(ValueError, "no eligible"):
            validate_public_items({"perspective": "p2", "protocol_prefix": [], "view": {"opponent_team": [{"ident": "p1: One", "item": "has-item"}]}})

    def test_owned_item_history_survives_reentry_without_inventing_a_writer(self):
        from neural.public_item import validate_public_items
        prefix = ['|switch|p1a: Eater|Snorlax|100/100', '|-enditem|p1a: Eater|Sitrus Berry|[eat]',
                  '|switch|p1a: Bench|Snorlax|100/100', '|switch|p1a: Eater|Snorlax|67/100']
        row = {'ident': 'p1: Eater', 'item': None, 'item_state': 'consumed', 'last_item': 'sitrusberry', 'item_suppressed': False}
        observation = {'perspective': 'p1', 'protocol_prefix': prefix, 'view': {'self_team': [row]},
                       'request': {'side': [{'ident': 'p1: Eater', 'item': None}]}}
        validate_public_items(observation)
        for field, value in [('last_item', 'leftovers'), ('item_state', 'removed')]:
            bad = copy.deepcopy(observation); bad['view']['self_team'][0][field] = value
            with self.assertRaisesRegex(ValueError, 'Public item'):
                validate_public_items(bad)
        for field, value in [('last_item', 'sitrusberry'), ('item_state', 'consumed')]:
            bad = copy.deepcopy(observation); bad['protocol_prefix'] = []
            bad['view']['self_team'][0] = {'ident': 'p1: Eater', 'item': None, 'item_state': 'unknown', 'last_item': None, 'item_suppressed': False, field: value}
            with self.assertRaisesRegex(ValueError, 'no matching retained public writer'):
                validate_public_items(bad)

    def test_terminal_item_suffix_replacement_stops_disguise_alias_and_missing_item_stays_unknown(self):
        from neural.public_item import validate_public_items
        rows = [{'slot': 1, 'ident': 'p1: Actual', 'name': 'Actual', 'base_species': 'Zoroark', 'item': 'leftovers', 'item_state': 'held', 'last_item': None, 'item_suppressed': False},
                {'slot': 2, 'ident': 'p1: Disguise', 'name': 'Disguise', 'base_species': 'Snorlax', 'item': None, 'item_state': 'consumed', 'last_item': 'sitrusberry', 'item_suppressed': False},
                {'slot': 3, 'ident': 'p1: Unknown', 'name': 'Unknown', 'base_species': 'Eevee', 'item': 'unknownprivate', 'item_state': 'unknown', 'last_item': None, 'item_suppressed': False}]
        prefix = ['|switch|p1a: Disguise|Snorlax|100/100']
        predecessor = {'schema_version': 'observable-battle-state/v2', 'battle_id': 'ordered-authority', 'perspective': 'p1', 'protocol_prefix': prefix,
                       'request': {'side': [{'ident': 'p1: Actual', 'active': True, 'item': 'leftovers'}, {'ident': 'p1: Disguise', 'item': 'sitrusberry'}, {'ident': 'p1: Unknown'}]}, 'view': {'self_team': copy.deepcopy(rows)}}
        successor = {**predecessor, 'request': None, 'protocol_prefix': prefix + ['|replace|p1a: Actual|Zoroark|100/100', '|-enditem|p1a: Disguise|Sitrus Berry|[eat]'],
                     'view': {'self_team': rows, 'terminated': True}}
        validate_public_items(successor, predecessor)
