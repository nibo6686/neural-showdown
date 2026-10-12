# Hygiene report (final)

## A. Windows stdin decoding - verified
Helper piped raw UTF-8 JSON ("Pokemon" with accent) into `python -c ... json.load(sys.stdin)`, decoded as cp1252 on Windows. Fixed both inline reads in public_consequence_test_helpers.ts (identity-only verifier; assertFreshPythonRejections batch) with `json.loads(sys.stdin.buffer.read().decode('utf8'))`. No PYTHONUTF8. Revival real p1 and real p2 tests pass with PYTHONUTF8 and PYTHONIOENCODING unset.
Same latent pattern, not edited (no failure shown): ability_callback.test.ts:112, item_identity.test.ts:870, protocol_contract_validation.test.ts (~169,422,466,691), psych_up.test.ts:200,213, psych_up_validation.test.ts:46,55,70.

## B. Imposter test - fixture defect, not production
Before: failed with "Public ability evidence mismatch". Cause: fixture Pawmot had no Ability line, so the copied owner-request ability was '' while baseAbility (Imposter) made state_extractor.ts ~459 emit 'known'. Check: Teams.generate('gen9randombattle') over 300 seeds produced 1800 sets, 0 with an empty ability, so a null owner-request ability cannot arise in real random-battle play. Fix: `Ability: Iron Fist` added to the p2 Pawmot in revival.test.ts copiedFixture. No production code changed. All 11 revival tests pass. Residual: a hand-imported ability-less team would still project 'known' with null ability; left as an unreachable-in-scope note, since identity-sensitive suites were not touched.

## C. CRLF - done and verified
.gitattributes `-text` entries added; both JSON files refreshed from index. segment-start.json sha256 a468592b...27c5 and the faithful "saved win tie and bound" test (module-load hash assertion included) passes. CE-08A long test not run.
