# LIVE event enrichment — backend field → event field → frontend consumer

Goal: make REAL (Mistral/live) runs emit the information the backend already
holds, so the existing frontend panels show real data instead of empty states.
All enrichment is **additive** (new optional fields); existing fields/types are
unchanged, so no backend or frontend consumer breaks.

Root cause: DEMO mode ships hand-authored rich `data` payloads; LIVE events
carried only the minimum (mostly `task_id` + `tool`). The backend state
(ToolResult, RecoveryDecision, VerificationReport, MemoryResult, plan/attempts,
`duration_ms`) already knew more — it just wasn't placed on the event `data`.

| Event | Field added | Source (real backend state) | Frontend consumer |
|-------|-------------|-----------------------------|-------------------|
| PLAN_CREATED | objective, task_count, task_names, planner, model | `state.objective`, `plan.tasks`, `provider.name`, `provider.model` | plan-panel, timeline, result |
| MEMORY_RETRIEVED | memory (singular), count | top `MemoryResult` (`record.id/scope/tags/content`, `score`) | memory-panel (`evt.data.memory`) |
| TASK_STARTED | tool, node | `task.tool` | plan-panel, stage ribbon |
| TOOL_STARTED | action, args, command/path/url/environment, node | `task.tool_args` | tool-panel, timeline, stage ribbon |
| TOOL_COMPLETED | duration_ms, exit_code, output_summary, node | `result.duration_ms`, `result.metadata.returncode`, `result.output` | tool-panel (`duration_ms`), result |
| TEST_STARTED | command, suite, node | `task.tool_args.command` | test-panel |
| TEST_PASSED | passed, failed, skipped, total, exit_code, suite, duration_ms | parsed from real pytest stdout | test-panel, result |
| TEST_FAILED | passed, failed, total, failures, failure_class, exit_code, suite | parsed from real pytest stdout/error | test-panel, result |
| CODE_CHANGED | file, summary, node | `task.tool_args.path`, `result.output` | code-diff, result (`file`) |
| RECOVERY_STARTED | strategy, reason, diagnosis, failure_class, failed_tool, failure, retry, recovery_stage, node | `RecoveryDecision`, `task.result`, `task.attempts` | recovery-panel |
| PLAN_REVISED | revision, node | `plan.revision` | plan-panel |
| VERIFICATION_COMPLETED | summary, checks_passed, checks_total, node | `VerificationReport` | result, timeline |
| MEMORY_STORED | memory_id, scope, tags, node | returned `MemoryRecord` | result (`memory_id`) |
| OBJECTIVE_COMPLETED | status, objective, summary, verified, plan_revisions, tool_calls, recoveries, files_changed, node | `state`, event history | result, timeline |
| OBJECTIVE_FAILED | status, error, failure_stage, recovery_status, node | `state.error`, `state.node`, history (keeps existing `error_type`) | result (`error`) |

Security: only non-sensitive fields are surfaced. Tool args are truncated and
never include env/credentials (the toolbelt takes paths/commands, not secrets).
Memory is surfaced as id/scope/tags + a truncated content summary — never
embeddings, `user_id`, or raw stored blobs.

`node` is a coarse UI-stage hint (INSPECT/CODE/TEST/DEPLOY/VERIFY/RECOVERING/
LEARN) derived from the tool/phase, used only to advance the pipeline ribbon;
the frontend reads it as `evt.node || evt.data.node`.
