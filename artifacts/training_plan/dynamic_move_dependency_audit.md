# Dynamic Move Dependency Audit

This is a narrow dependency inventory for `legal-action-v5` resolved impact.
“Likely covered” means the current damage request already carries the required
state and `@smogon/calc` implements the mechanic; it is not a substitute for a
focused counterfactual test.

| Move/mechanic | Dependency | Current status | Note |
| --- | --- | --- | --- |
| Rage Fist | Times the user has been successfully attacked | **Fixed** | Tactical reconstruction now tracks a per-species counter from complete protocol history and passes `times_attacked`; unknown history fails closed. |
| Last Respects | Fainted allies | **Known broken** | Tactical state knows fainted species, and calc supports `alliesFainted`, but the damage request does not pass it. |
| Stored Power / Power Trip | Positive stat boosts | **Known broken / verify after plumbing** | Calc supports boost counting, but live tactical boosts are not currently merged into the damage attacker payload. |
| Facade / Hex / Venoshock | User or target status | **Likely covered** | Attacker and defender statuses are merged from tactical state and calc implements these modifiers. Add focused tests. |
| Eruption / Water Spout / Reversal / Flail | Current/max HP | **Likely covered** | Request/view HP fraction or exact HP is passed and calc implements HP scaling. Add boundary tests. |
| Grass Knot / Low Kick / Heavy Slam / Heat Crash | Species weight / weight ratio | **Likely covered** | Calc derives canonical species weights. Forme and weight-changing edge cases need verification. |
| Gyro Ball / Electro Ball | Attacker/defender Speed | **Needs verification** | Calc implements speed ratios and receives stats, but opponent inference and missing tactical speed-stage plumbing can make live values stale. |
| Body Press / Foul Play | Defense or target Attack as attacking stat | **Needs verification** | Calc implements nonstandard attacking stats; exact-stat and boost-stage parity should be tested. |
| Knock Off / Acrobatics | Target/user held item | **Likely covered when item known** | Private item and public/belief target item are passed; unknown or inferred opponent items remain uncertainty. |
| Weather Ball / Terrain Pulse | Weather/terrain and grounding | **Likely covered** | Tactical weather/terrain is passed and calc implements power/type changes; grounding edge cases need verification. |

## Schema Note

The Rage Fist fix corrects values in existing v5 resolved-impact fields. It does
not add, remove, rename, or reorder features, so the action schema remains
`legal-action-v5` at 318 dimensions.

Existing v5 materializations and checkpoints are mechanically stale for Rage
Fist because their resolved-impact values were generated with static 50 BP.
They are not silently relabeled as corrected. No dataset was rematerialized and
no checkpoint was promoted.
