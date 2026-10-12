# Prompt22 independent read-only review

Reviewer: fresh `jirachi`, requested gpt-6.1-sol/high, project Pokémon naming,
read-only/no descendants. Effective settings and pricing are not exposed. Parent
alone authored/integrated shared files. No reviewer files or historical outputs
were written.

Review covered current source capabilities versus proposed authority, immutable
identity/privacy, delivery sequence/cursor, restoration and test-plan wiring.
Independent native inline probe (gen9customgame, three literal sets, resolved team
preview then switch2) observed duplicate nicknames, current→original [2,1,3],
serialized order213 and matching restored order. That is pinned mechanic evidence,
not supported random-team generation or provider adoption. Parent's new controls
separately exercise actual random generation and gen9randombattle literal probes.

Two source findings integrated before final design: pipeline candidates create
new env-local counters, so committed request sequence must be session-owned;
requests emit before update fanout, so cursor binds settled exact prefix rather
than asynchronous receipt. Current Prompt16 repair is distinguished from Prompt15
historical stale-request observations.

Final review found one wording gap: TS/Python proposed factory/serialization gates
could imply transporting process-local provider authority. Parent added explicit
nonserializable capability and separately authorized creation-owner bridge
prerequisites. Reviewer confirmed the clarification resolves the finding.

Fresh independent command, cwd `sim-core`:

```powershell
Remove-Item Env:PROMPT22_REPORT,Env:NODE_OPTIONS,Env:PYTHONIOENCODING,Env:PYTHONUTF8 -ErrorAction SilentlyContinue
node --test --test-isolation=none --test-reporter=spec dist/tests/original_owner_provider_characterization.test.js
```

Exit0;10/10 passing, zero skipped; no report writer. No remaining scoped blocker
for this **design/source-proof checkpoint**. The proposed getTeam observer is
plausible but unproved; callback completeness, drag, event indexing and restoration
need their own gate. Provider, ledger, crosswalk and cross-process source authority
remain unimplemented/unproved. No fact semantics, completeness or fidelity claim.
