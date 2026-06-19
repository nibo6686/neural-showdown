# vNext Training Cost Estimate

**State:** v7, 3208 floats  
**Action:** v5, 318 floats  
**Observed 15k pool:** about 46 state examples and 50 action decisions per battle;
about 5.38 legal candidates per action decision.

## Dense storage per vector

| Payload | float32 | float16 |
| --- | ---: | ---: |
| One state vector | 12,832 B (12.53 KiB) | 6,416 B (6.27 KiB) |
| One action vector | 1,272 B (1.24 KiB) | 636 B (0.62 KiB) |
| One state + one action candidate | 14,104 B (13.77 KiB) | 7,052 B (6.89 KiB) |

## Expected scale

| Battles | State examples | Action decisions | Candidate rows |
| ---: | ---: | ---: | ---: |
| 300 | 13.8k–15k | 13.8k–15k | 74k–81k |
| 1,000 | 46k–50k | 46k–50k | 247k–269k |
| 5,000 | 230k–250k | 230k–250k | 1.24M–1.35M |
| 15,000 | 690k–750k | 690k–750k | 3.71M–4.03M |

State-only dense float32 storage is roughly 0.17–0.19 GB, 0.59–0.64 GB,
2.95–3.21 GB and 8.85–9.62 GB respectively; float16 halves those figures.

If action-ranker files duplicate the 3208D state for every candidate, combined
float32 rows are roughly 1.0–1.1 GB for 300 battles, 3.4–3.8 GB for 1,000,
17–19 GB for 5,000 and 52–57 GB for 15,000 before compression. Storing one state
per decision plus separate action arrays/group offsets is substantially cheaper.

## Bottlenecks and recommendation

Feature building is likely dominated by repeated trajectory-prefix parsing,
opponent-belief reconstruction, tactical reconstruction and per-candidate
Smogon damage calls. Cache battle prefixes/state features and batch or memoize
resolved impacts where inputs repeat.

On an RTX 2060 SUPER 8GB, the 3208D dense input and candidate grouping will
constrain batch size more than the current 115D model. Start with float16/bfloat16
mixed precision where stable, batch size 64–128 for state models and 16–64
decision groups for rankers, with gradient accumulation if needed. Measure peak
memory rather than assuming these values.

Dense storage is acceptable for `diagnostic_300` and probably `small_1000`,
especially with float16 and compressed containers. For medium/full runs, avoid
duplicating state vectors per candidate. Defer sparse/embedding architecture
work until dense diagnostic benchmarks establish whether hashing sparsity and
I/O are actual bottlenecks.
