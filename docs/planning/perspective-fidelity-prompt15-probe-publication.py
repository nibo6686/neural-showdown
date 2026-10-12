"""Prompt 15 probe: what the existing Python validators do with an added sidecar key / nested raw_request (test-owned, read-only)."""
import copy, json, sys
from pathlib import Path
from neural.pipeline_record import validate_pipeline_bundle, PipelineRecordError
cases = {"ordinary_slots": json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))}
out = {}
for version in ("observable-battle-state/v1", "observable-battle-state/v2"):
    b = cases["ordinary_slots"]["versions"][version]["bundles"]["p1"]
    base = validate_pipeline_bundle(b)
    row = {"baseline_ok": True, "data_record_id": base["record_id"] if "record_id" in base else sorted(base)[:3]}
    def attempt(label, mutate):
        c = copy.deepcopy(b); mutate(c)
        try: validate_pipeline_bundle(c); row[label] = "accepted"
        except PipelineRecordError as e: row[label] = "rejected: " + str(e)[:110]
    attempt("extra_sidecar_key", lambda c: c.update(request_knowledge={"schema_version": "request-knowledge/v1"}))
    attempt("sidecar_with_raw_request_key_nested_in_extra", lambda c: c.update(request_knowledge={"raw_request": "{}"}))
    attempt("new_bundle_schema_version_v2", lambda c: c.update(schema_version="pipeline-linked-record/v2"))
    out[version] = row
print(json.dumps(out, indent=1))
