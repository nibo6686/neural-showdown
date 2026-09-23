# Model Manifest

Initial contract placeholder for model compatibility and `CTRL-001` controls.

Each model artifact should declare model family, checkpoint path or immutable artifact ID, feature schema/version/fingerprint, action schema/version/fingerprint, observation regime, dataset source kinds, split policy, simulator version, seed policy, training commit, and validation report. Missing or incompatible metadata must fail closed; padding, truncation, or public-model fallback must not be implicit.

