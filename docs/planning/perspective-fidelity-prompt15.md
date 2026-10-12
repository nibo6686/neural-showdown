# Prompt 15 — S01c design checkpoint (no production edits)

Inputs: prompt14-lead-review.md, REQUEST_KNOWLEDGE.md, prompt13-design.md (restored-branch stale request, terminal request:null), perspective-knowledge docs (PERSPECTIVE_KNOWLEDGE.md, typed-references.json), prompt12 source seam, implementation plan roadmap (S01c, S03, PK-02B-Publish), docs/contracts/PIPELINE_EPISODE.md, DATASET_LINEAGE.md, OBSERVABLE_STATE.md, BELIEF_STATE.md.

Deliverable: a design document docs/planning/perspective-fidelity-prompt15-design.md plus evidence (progress, report <1000 words, hashes, protected baseline). Writes: new docs/planning files only, plus (optional) new characterization tests proving the restoration/terminal facts below. No edit to any existing file.

Determine, with source-backed evidence and real runs:
1. Where in pipeline_integration.ts / env_manager.ts the raw addressed request text is available per boundary (StepResult.requests[owner].raw, ManagedPlayer chunk routing) and whether it is byte-exact there; what must be retained per boundary and for how long.
2. The restored/snapshot-branch stale request defect (prompt13): diagnose the cause (toJSON/activeRequest/restore path) with a minimal reproduction; propose the smallest env_manager fix or restoration key, and whether it changes any existing seeded-restoration identity or the accepted episode evidence.
3. Terminal/waiting/requestless retention: what the sidecar should record vs what legacy keeps (request:null), without fabricating.
4. Publication options for carrying the sidecar in bundles/episodes without changing existing v1/v2 observation, belief, transition, DATA, bundle or episode identities: new bundle/episode versions vs an optional parallel sidecar field vs separate joined artifact. Exact file/key list, exact validators in Python/TS to touch, version names, backward compatibility, blast radius (cf. rejected v3 observation), and how faithful_complete_episode eligibility would or would not change (it must not silently change).
5. The K-fact adapter: mapping request-knowledge to PERSPECTIVE_KNOWLEDGE facts with derived flags emitted as unknown; roster/broadcast rule for per-active versus per-move subjects; where it plugs into the Prompt 12 seam.
6. Recommended split into reviewable S01c-1..n boundaries with write sets, red tests, risks, and what the lead must decide. State rejected alternatives. Flag every spot where production identity or legal authority could change.

No production change, no commits/staging/installs. Python D:\Anaconda\envs\neuralgpu\python.exe, PYTHONPATH=trainer/src, PYTHON set, PYTHONUTF8/PYTHONIOENCODING unset, long commands in background.
