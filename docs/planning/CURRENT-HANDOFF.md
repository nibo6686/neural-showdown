# Current development handoff — 2026-10-12

Read this before the older perspective-fidelity-HANDOFF.md. That document is
historical through Prompt16; this document and the current implementation plan
govern continuation. The supplied conversation Markdown is context, not blanket
authorization to rerun its old prompts.

## Checkpoint and next work

The transfer branch is codex/perspective-fidelity-handoff, based on merged
accab655c26ada18124e790b16d5770c8bd17894. This is a local development snapshot,
not publication or final readiness. The user explicitly authorized this handoff
commit; earlier no-commit instructions remain historical. No push is authorized.

Prompts 1–25 have bounded dispositions in perspective-fidelity-implementation-
plan.md. The latest accepted work is private original-team retention (23),
native request emission/receipt capture (24), and committed session delivery
selection/parent/prefix history (25). The lead re-ran 179 focused passing checks, build,
wire equality and preservation; the three broader requirement failures remain
red. Prompt26 is prepared but has NOT begun.

Next read perspective-fidelity-prompt25-lead-review.md and execute only
perspective-fidelity-prompt26-implementation.md: tests/docs source proof of
native birth/request/indexed appearance/restoration associations before runtime
crosswalk coding. No current action authority, carrier, registry/provider
adoption, Python authority bridge, knowledge facts or completeness is implied by 25.
The internal ledger is trusted session machinery, not arbitrary-input
authentication. FIFO and equal-byte injection limitations remain explicit.

Strong goal: accurate legitimate state/knowledge for both players at every
supported boundary before training. Persistent original owner knowledge,
chronological current/public state and request authority stay distinct.
The existing faithful_complete_episode flag retains its pinned capture/continuity
meaning. Strong perspective completeness remains unverified.

Public replay policy: uniquely attributable own starting facts revealed anywhere
may be backfilled from turn1; never-revealed/ambiguous facts remain unknown.
Copied/acquired moves, opponent information and dynamic state keep chronology.
Local native proofs cannot certify public replay originals. Both supplied
HTML files and expected-ledger.json are committed under
trainer/tests/fixtures/perspective-replay; original Downloads paths are unnecessary.

## Lead/implementation workflow

Use the project-lead skill as governing lead. Separate bounded implementation
and fresh independent review; use subagents to manage context and follow the
Pokemon naming convention in the transferred project config. One writer owns
shared source. Read docs/refactor/AGENT_PROTOCOL.md and docs/codex_review_state.md;
its older dated decisions are history, superseded by current initiative reviews.
Only lead updates aggregate status. Do not rewrite old reports or self-attest.

No automatic later-task implementation, contract revision, source/assurance
promotion, datasets/training, server/model workload, commit/push/merge or
publication is authorized by opening a new conversation. User can authorize
those separately. Prompt26 is the prepared next assigned boundary.

## New-machine setup

Transfer the entire handoff directory described in TRANSFER-README.md plus the
conversation transcript. Git bundle carries history/commit; exact-worktree.zip
preserves original evidence bytes; supporting-materials.zip carries skills,
safe project config, pinned-source witnesses, five existing LFS objects and
the earlier evidence snapshot. No global auth or personal settings are included.
Ignored bulk data/generated artifacts (~8GB) are excluded; they are not required
for these development gates and need a separate transfer if wanted later.

Recorded machine: Windows, Node24.15.0, Python3.11.14. Use the committed sim-core
package-lock.json with npm ci on the destination. No dependency installation or
new-machine validation was performed during packaging. Direct compiler:
node node_modules/typescript/bin/tsc -p tsconfig.json from sim-core.
Old installed npm shims were unreliable; do not copy node_modules.

Python needs NumPy and PyTorch for loader imports even though no checkpoint
workload runs; installed versions are recorded in python-packages-reference.json.
This inventory describes the old environment, not a supported universal lock.
Choose a destination-compatible PyTorch build; CUDA is unnecessary for the
focused import/tests. Existing trainer optional profiles/locks remain as recorded.
Set PYTHON to the destination executable and PYTHONPATH to absolute trainer/src.
Keep PYTHONUTF8/PYTHONIOENCODING unset for transport checks.

Use docs/planning/run-handoff-validation.ps1 -Python <destination-python>.
It writes NEW logs outside the repository and repeats the 179 focused passing checks plus
the expected one TS/two Python requirement failures. Node files run separately.
Do not execute historical validate/package scripts blindly: many hardcode
D:/Anaconda paths and overwrite historical logs. New machine means fresh evidence.

Git EOL conversion can change raw historical hashes without changing normalized
code. Prefer the verified exact-worktree.zip overlay for byte-for-byte continuation;
its manifest verifies raw files. Historical hash inventories/absolute paths describe
their original candidate, not a newly cloned normalized tree. Raw data/symbol/
undefined provenance stays private; no serialized diagnostic grants authority.

## Give the next conversation

Provide this document, the transcript and the repository checkout. Useful
entry points are the implementation plan, latest lead review, Prompt26,
PERSPECTIVE_KNOWLEDGE.md, REQUEST_KNOWLEDGE.md and Prompt23/24/25 APIs.
The checkout already includes historical diffs/reports/literal witnesses,
contracts/fixtures, repo skills and mirrored .claude/skills. Install the
transferred custom Codex skills into the new machine's selected skill scope;
do not copy authentication/session databases.

Start prompt:
“Act as project lead. Read docs/planning/CURRENT-HANDOFF.md and the attached
transcript as historical context. Verify the transferred commit and environment,
then continue the prepared Prompt26 boundary with separate implementation and
independent review. Preserve all current scope and training gates.”
