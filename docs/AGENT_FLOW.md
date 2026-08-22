# KALKI Agent Flow

The orchestrator (`agent/orchestrator.py`) is an explicit state machine over a
single, persistent `AgentState`. Each node mutates the state and returns the
next node's name.

## State machine

```
        START
          │
          ▼
   UNDERSTAND_OBJECTIVE ── record objective in session memory
          │
          ▼
     CREATE_PLAN ─────────── recall long-term memory → plan → PLAN_CREATED
          │
          ▼
 ┌► SELECT_NEXT_TASK ───────── plan complete? ──yes──► VERIFY
 │        │ no (pick task whose deps are done)
 │        ▼
 │   EXECUTE_TOOL ──── permission gate ──blocked──► AWAITING_APPROVAL (pause)
 │        │ allowed
 │        ▼
 │   OBSERVE_RESULT ── ok? ──yes──► mark COMPLETED ─┐
 │        │ no                                       │
 │        ▼                                          │
 │   DECIDE_NEXT_ACTION                              │
 │        ├─ RETRY   → reset task to pending ────────┤
 │        ├─ REPLAN  → insert remediation, revise ───┤
 │        ├─ ESCALATE→ AWAITING_APPROVAL (pause)     │
 │        └─ ABORT   → mark FAILED ──► STORE_MEMORY  │
 └────────────────────────────────────◄─────────────┘
          │
          ▼
       VERIFY ──────────────── independent checks → VERIFICATION_COMPLETED
          │                    (sets COMPLETED or FAILED)
          ▼
     STORE_MEMORY ──────────── persist long-term experience → OBJECTIVE_(COMPLETED|FAILED)
          │
          ▼
         END
```

The loop is **bounded**: task retries ≤ `max_task_retries`, plan revisions ≤
`max_plan_revisions`, and a global step budget guards against any cycle.

## Pause / resume (human-in-the-loop)

When a task needs a gated (elevated/dangerous) tool and no approval exists, the
run emits `APPROVAL_REQUIRED`, sets status `AWAITING_APPROVAL`, and the drive
loop returns — the state is fully serialised. Calling
`Orchestrator.resume(state, approvals=[...])` (or `POST /approve`) grants the
approval and continues from exactly where it stopped.

## Event lifecycle

Every node emits `AgentEvent`s (buffered, replayable). Types:

| Phase | Events |
|---|---|
| Planning | `PLAN_CREATED`, `PLAN_REVISED`, `MEMORY_RETRIEVED` |
| Task | `TASK_STARTED`, `TASK_COMPLETED`, `TASK_FAILED` |
| Tools | `TOOL_STARTED`, `TOOL_COMPLETED`, `TOOL_FAILED`, `CODE_CHANGED` |
| Tests | `TEST_STARTED`, `TEST_PASSED`, `TEST_FAILED` |
| Deploy | `DEPLOY_STARTED`, `DEPLOY_COMPLETED` |
| Recovery | `RECOVERY_STARTED`, `APPROVAL_REQUIRED` |
| Verify | `VERIFICATION_STARTED`, `VERIFICATION_COMPLETED` |
| Memory | `MEMORY_STORED` |
| Terminal | `OBJECTIVE_COMPLETED`, `OBJECTIVE_FAILED` |

## Worked example (from `scripts/demo.py`)

Objective: *"Fix the authentication bug, test the fix, deploy it, and verify."*

```
[ 2] PLAN_CREATED           Plan with 4 tasks
[ 4] TOOL_STARTED           list_dir           # inspect
[ 8] TOOL_STARTED           write_file          # the fix
[10] CODE_CHANGED           working tree modified
[13] TEST_STARTED / TEST_PASSED
[17] TOOL_STARTED           flaky_deploy
[18] TOOL_FAILED            registry timeout (transient)
[19] RECOVERY_STARTED       retry: transient; attempt 1 within limit
[22] TOOL_COMPLETED         ok                  # succeeded on retry
[25] VERIFICATION_COMPLETED plan_complete=ok; tests_passed=ok; deploy_smoke=ok
[26] MEMORY_STORED
[27] OBJECTIVE_COMPLETED    objective complete and verified
```

This is the required `objective → plan → tool → failure → recovery → success`
path, and it is exercised deterministically by
`tests/test_orchestrator.py::test_integration_objective_plan_tool_failure_recovery_success`.
