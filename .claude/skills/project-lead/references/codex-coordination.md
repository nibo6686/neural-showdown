# Codex persistent coordination

Read this reference only when persistent Codex task tools are available and the user has authorized creating a lead-worker pair.

## Establish the pair

- Keep the lead on the initiative's governing route and use `route-agent-work` for the worker route.
- Use `list_threads` to resolve the current lead task and any existing initiative section. Otherwise use `create_sidebar_section`, then place the lead and worker tasks with `move_thread_to_sidebar_section`.
- Create the worker with `create_thread` only under the user's task-creation authority. Resolve real task IDs rather than guessing them. If creation returns only a client ID while setup is pending, wait for the real task ID before moving or messaging the task.
- Give the worker the lead task ID and host ID as part of its return contract.

## Supervise by callback

After the worker accepts the lane, let the lead task go inactive unless the lead has independent work that can materially affect the worker's next action. Resume on a planned checkpoint, material scope or risk change, decision blocker, or completion callback; do not poll merely to observe progress.

Require the worker to notify the lead with `send_message_to_thread` once per planned checkpoint, material reclassification, completed lane, or decision-blocking return. The callback should contain the result, changed assumptions, diff or commit, validation, unresolved risks, and exact next action. A final response left only in the worker task is not a completed handoff.

When the callback resumes the lead, review and integrate the return or send a bounded revision to the same worker. If the user steers the worker directly, reconcile that task before the next lead decision so initiative ownership does not split.
