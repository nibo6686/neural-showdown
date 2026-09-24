# Model Manifest

**Status:** Initial design placeholder only; no new-model manifest contract has
been accepted. FEATURE-001, the target/reward definition, and the training/
inference interface remain unresolved. See [PROJECT_STATUS.md](../PROJECT_STATUS.md).

This page records future design questions, not a schema that collectors or
loaders may claim to satisfy. A later versioned contract should explicitly
define model family and immutable artifact identity; feature/action schema IDs
and fingerprints; observation/information regime; data source and split policy;
simulator and source commit provenance; seed/config/dependency metadata; input
and output schemas; inference validation and batching; and the validation
report associated with the artifact. Incompatible or unknown schemas must fail
closed. Silent padding, truncation, and cross-regime fallback are not acceptable
compatibility rules.

Existing legacy and vNext checkpoints are intentionally abandoned for the new
approach and are non-blocking. This placeholder does not promote, load, fetch,
or assess any old checkpoint.
