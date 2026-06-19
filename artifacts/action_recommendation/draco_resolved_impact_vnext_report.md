# Draco Meteor Resolved Impact vNext Report

**Date:** 2026-06-19  
**Schema:** diagnostic `legal-action-v5` (318D)

`legal-action-v5` exposes Draco Meteor's immediate resolved damage: expected,
minimum and maximum damage fractions, KO chance, accuracy, effectiveness and
calculation provenance.

Its exact 269D `legal-action-v4` prefix independently preserves Draco Meteor's
raw self SpA -2 consequence as normalized `self_stat_delta_spa=-1.0` and
`self_has_stat_drop=1`. This separates two different facts:

- v5 resolved-impact fields describe the immediate hit into the current target;
- v4 consequence fields describe the move's known self-drop.

The post-Draco position with actual SpA -2 is represented in the next state by
the versioned state features. It appears as a next-state action delta only when
the dataset/provider supplies a seeded branch or generated next-state delta
label. An immediate damage estimate alone does not authoritatively populate all
future HP, status, field, terminal or strategic consequences.

Resolved impact is therefore not full future-position evaluation. It improves
action context without adding a hardcoded Draco penalty, changing live defaults
or replacing transition-derived action-value training.
