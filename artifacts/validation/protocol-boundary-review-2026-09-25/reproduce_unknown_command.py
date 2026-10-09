"""Reproduce the assessment's fully rehashed protocol-publication bypass."""
import io
import json
import sys
from unittest.mock import patch

from test_pipeline_record import _bundle, _rehashed_protocol_candidate
from neural.pipeline_record import PipelineRecordError, main, validate_pipeline_bundle
from neural.ts_identity import verify_bundle_identities


bundle = _bundle(version="v2")
candidate = _rehashed_protocol_candidate(bundle, "input", "|futuremechanic|opaque")
verify_bundle_identities(candidate)

try:
    validate_pipeline_bundle(candidate)
except PipelineRecordError as exc:
    rejection = str(exc)
else:
    raise AssertionError("fully rehashed unknown command was published")

stdout, stderr = io.StringIO(), io.StringIO()
with patch("sys.stdin", io.StringIO(json.dumps(candidate))), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
    status = main()
if status != 2 or stdout.getvalue():
    raise AssertionError(f"CLI emitted output for rejected bundle: status={status}, stdout={stdout.getvalue()!r}")

print(json.dumps({
    "case": "rehashed |futuremechanic|opaque in input and successor prefixes",
    "identity_joins": "verified before publication validation",
    "record_validation": "rejected",
    "rejection": rejection,
    "cli_status": status,
    "stdout_bytes": len(stdout.getvalue().encode("utf-8")),
}))
