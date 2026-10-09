Work item: <WORK-ITEM-ID>

Read:
- docs/refactor/STATUS.md
- docs/refactor/WORK_ITEMS.md
- the assigned work item
- relevant contract documents

Do not perform a repository-wide scan.

Before editing:
1. Restate the contract being changed.
2. Identify the smallest safe implementation slice.
3. List files that may change.
4. Define tests and acceptance criteria.
5. Define rollback behavior.

During implementation:
- Do not silently coerce incompatible state or actions.
- Do not weaken validation to make tests pass.
- Preserve raw protocol evidence.
- Keep observable facts separate from beliefs.
- Avoid unrelated cleanup.
- Update schema/version metadata when behavior changes.

After implementation:
- Run the narrowest available tests.
- Record exact commands and results.
- Update the assigned agent note.
- Report files changed, validation, limitations, risks, and next work item.

If dependencies prevent testing, record the blocker and do not claim validation.
