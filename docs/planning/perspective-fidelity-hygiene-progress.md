# Hygiene worker progress (2026-10-10)

- A: DONE (edit) / NOT VERIFIED. public_consequence_test_helpers.ts: both inline python stdin reads now `json.loads(sys.stdin.buffer.read().decode('utf8'))`. Build/test could not run: sim-core/node_modules is empty (directory mtime 19:56, emptied by something other than this worker; no install permitted).
- B: BLOCKED. Static trace only (see report); no code or fixture change made.
- C: DONE. .gitattributes `-text` entries appended (CRLF to match the file's working-tree endings); segment-start.json and predecessor.json re-checked out from index. Load assertion of pipeline_episode_faithful.test.js NOT run (no node_modules).
