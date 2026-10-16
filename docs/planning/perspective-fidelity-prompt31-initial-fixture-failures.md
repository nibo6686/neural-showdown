# Initial fixture failures — preserved disposition

No production correction was needed. Exact failed command entries remain in commands.json; the initial historical-TS-readers.log retains the terminal construction stack. The pre-edit-output-control log contains the corrected successful attempt; this note preserves the earlier failed sweep baseline generation from tool output rather than rerunning it:

- Initial terminal fixture: `Error: evidence-terminal-perspectives`, from terminalEvidence while createPipelineEpisodeEvidence constructed the test fixture. Added the missing terminal snapshot_phase.
- Initial sweep fixture: `p31_old_reader.PipelineRecordError: episode publication sweep belief 0 fields fields are not exact; missing=[], unexpected=['contradictions', 'unresolved']`. Moved these required histories into their specified compact arrays. The original validator rejection was preserved and its rules unchanged.

The two necessary rebuilds were limited to test fixture corrections; only the affected fixture case and initially unrun checks were executed. Unchanged passing dispatch/negative controls were reused. No timeouts, broad suite or native battle occurred.
