---
name: wm-adr
description: Generate a West Monroe-style architecture decision record from the current decision context.
---

Generate an Architecture Decision Record based on the current conversation context and any explicit decision topic provided.

If a topic is provided, focus on that decision. Otherwise, identify the most significant architectural decision in context and document it.

Produce the ADR in the following West Monroe format:

## ADR-[NNN]: [Short Title — Present Tense Decision Statement]

**Date:** [TODAY'S DATE]
**Status:** Proposed

**Deciders:** [Names if known, otherwise "[Team]"]

### Context

[2–4 sentences describing the problem, constraints, and why the decision is needed now]

### Decision Drivers

- [Key factor 1]
- [Key factor 2]
- [Key factor 3]

### Options Considered

#### Option 1: [Name]
[Brief description]

Pros:
- [Pro 1]
- [Pro 2]

Cons:
- [Con 1]
- [Con 2]

#### Option 2: [Name]
[Brief description]

Pros:
- [Pro 1]

Cons:
- [Con 1]

#### Option 3: [Name] *(if applicable)*
[Brief description]

### Decision

We will **[chosen option]** because [1–2 sentence rationale tied to the decision drivers].

### Consequences

**Positive:**
- [What becomes easier or better]

**Negative / Trade-offs:**
- [What becomes harder, riskier, or more complex]

**Neutral:**
- [Material changes that are neither clearly positive nor negative]

### Follow-up Actions

- [ ] [Action 1]
- [ ] [Action 2]
- [ ] [Action 3]

End by recommending a file location such as `docs/adr/` or `architecture/decisions/` and a filename like `ADR-[NNN]-[kebab-case-title].md`.
