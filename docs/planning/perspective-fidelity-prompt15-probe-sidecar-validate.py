"""Prompt 15 probe: Python builder parity + validator on sidecars built at real pipeline boundaries (test-owned)."""
import json, sys
from pathlib import Path
from neural.request_knowledge import build_request_knowledge, validate_request_knowledge, canonical_request_knowledge_json
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
res = {"rows": 0, "validated": 0, "parity": 0, "presence": {}, "bytes_total": 0, "bytes_max": 0, "authority": {}, "failures": []}
for r in data["rows"]:
    res["rows"] += 1
    rec = r.get("record")
    if rec is None:
        res["failures"].append(["no-record", r.get("refused")]); continue
    try:
        out = validate_request_knowledge(rec, r["observation"])
        res["validated"] += 1
        res["authority"][out["delivery_authority"]] = res["authority"].get(out["delivery_authority"], 0) + 1
        py = build_request_knowledge(r["owner"], r["text"], r["observation"], "fresh_delivery")
        if canonical_request_knowledge_json(py) == canonical_request_knowledge_json(rec): res["parity"] += 1
        else: res["failures"].append(["parity", r["seed"], r["step"], r["owner"]])
        res["presence"][rec["presence"]] = res["presence"].get(rec["presence"], 0) + 1
        n = len(canonical_request_knowledge_json(rec)); res["bytes_total"] += n; res["bytes_max"] = max(res["bytes_max"], n)
    except Exception as e:
        res["failures"].append([type(e).__name__, getattr(e, "code", str(e))[:60], r["seed"], r["step"], r["owner"], r["kind"]])
res["failures"] = res["failures"][:10]
print(json.dumps(res, indent=1))
