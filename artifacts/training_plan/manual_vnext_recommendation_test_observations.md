# Manual vNext Recommendation Test Observations

## Replay Summary

The first manual display-only vNext shadow test is recorded as a **failure case
for recommendation quality**, despite successful packet/schema/slot validation.
The overlay remained advisory and the user manually chose all actions.

Observed behavior:

- vNext rarely or never recommended Tera;
- vNext rarely or never recommended switching;
- a forced-switch recommendation selected the first available option;
- in Annihilape versus Cresselia, after Annihilape took Psyshock, the
  recommendation/played action was Gunk Shot even though boosted Rage Fist was
  expected to be substantially better.

No command was automatically submitted and no live default changed.

## Extension Double-KO Switch Bug

On Turn 16, Arcanine used Flare Blitz, Meloetta fainted, and Arcanine then
fainted from recoil. Both players needed replacements.

The overlay checked the protocol-derived pending opponent replacement before
honoring our live `request.forceSwitch`. It therefore treated the state as
waiting for the opponent and did not send our legal switch-decision payload.

The decision ordering is fixed so a valid local `forceSwitch` request takes
priority over `request.wait` and pending-opponent replacement detection. Legal
switch actions are still derived from our request, existing decision-key dedupe
and payload behavior are unchanged, and nothing is auto-submitted.

## Model Behavior Triage

- **Tera avoidance:** consistent with the known validation weakness
  (`move_tera` top-1 approximately 0.178) and sparse imitation positives
  (approximately 1.8% of positives). This is primarily a ranker/label-coverage
  warning, not evidence of a slot or serving failure.
- **Switch avoidance / first-option forced switch:** consistent with only
  moderate switch validation performance (top-1 approximately 0.255), replay
  imitation labels, and limited evidence that the current features distinguish
  strategically good forced replacements. The first-slot result needs more
  examples before diagnosing a deterministic slot bias.
- **Overall:** successful schema and command serialization do not establish
  useful tactical behavior. The manual observations are materially worse than
  the offline aggregate metrics suggest.

## Annihilape vs Cresselia Failure Analysis

The most likely immediate cause is a **Rage Fist dynamic-power representation
and damage-resolution gap**, compounded by imitation learning:

1. The v5 impact path sends the move name to the Smogon calculator. Its Rage
   Fist entry has the unboosted static base power of 50.
2. The live damage payload does not supply Rage Fist's accumulated
   times-hit/attacks-received state, so taking Psyshock cannot increase the
   calculated Rage Fist damage.
3. Tactical parsing counts recent damage events internally, but that count is
   not part of the general v7 tactical state vector and is exposed in action
   features only for switch context. The ranker therefore lacks a clean
   move-specific signal connecting “Annihilape was hit” to stronger Rage Fist.
4. The ranker is trained by replay imitation: chosen actions are positives, but
   alternatives are not assigned tactical values. Sparse or noisy occurrences
   of boosted Rage Fist can reinforce the miss.

Likelihood assessment:

- Rage Fist dynamic-base-power/damage-resolution issue: **high**.
- v5 impact feature issue: **high**; resolved damage is likely based on 50 BP.
- Ranker imitation weakness: **moderate to high**, and likely amplifies the
  feature error.
- Sparse/biased replay labels for this interaction: **plausible**, but not
  established from this single replay.

No training or feature fix is attempted in this task.

## Training Gate Impact

This **blocks full-scale training and any promotion recommendation**. Scaling
the current pipeline would preserve a known move-mechanics blind spot and the
observed Tera/switch behavior has not met the manual display-only success
criteria. The diagnostic gate remains closed.

## Recommended Next Action

First re-run one double-KO replacement to confirm the overlay now emits a
force-switch display request. Then perform a narrow, read-only Rage Fist
diagnostic: replay the Annihilape/Cresselia state and compare the current v5
impact for Rage Fist before and after a recorded hit. Use that evidence to
specify the smallest dynamic-power state/impact correction before considering
more training. Continue display-only operation; do not promote or auto-submit.
