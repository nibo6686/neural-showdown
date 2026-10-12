# Prompt24 validation matrix

| Boundary | Independent control / production proof | Result |
|---|---|---|
| Missing implementation | Real session-created environment lacked trace accessor before edits | Red, exit 1 preserved |
| Native producer to receipt | Independent literal pushMessage and extractor-input taps; actual session-created environment | Green, both owners |
| Literal wire text | Unicode scalar text, whitespace, key order; exact JSON suffix and UTF-8 hex | Green; literal-witnesses.json |
| Repeated equal text | Repeated native producer calls, independent owner counters and global order | Separate FIFO occurrences |
| Owner/occurrence isolation | Other controller stream, wrong owner, copied/JSON handles, diagnostic token, local-counter collision | Rejected |
| Atomic supported inspection | Missing/duplicate/mismatched/distinct-text out-of-order receipts; pending owner queues | No usable partial trace |
| Restoration versus native | Delayed real owner-stream receipt gate; later native emissions before release | Producer origin retained |
| Force/wait/revival | Mirrored owner scenarios, actual legal switch/revival continuations | Green |
| Rejected choice | Trapped rejected switch native resend, then real moves | Green |
| Lifetime | Reset, terminal, terminal-history restore, failed initialization, disposal failure before await | Green |
| Existing wire | Fixed clock, v1/v2 initial result, boundary, snapshot, real step and bundles | Exact byte comparison green |
| Prompt23 preservation | Original-provider, source, session, restore, cleanup and settling tests | Green |
| Broader requirements | Separate original TS/Python requirement modes | Existing 1 TS + 2 Python failures remain |

The test-only taps and controlled teams are independent diagnostic oracles, not certificates, datasets or source-authority adoption. Same-byte arbitrary injected swaps are explicitly outside the detectable guarantee.
