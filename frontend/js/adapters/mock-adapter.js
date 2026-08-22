/**
 * KALKI — Deterministic Mock Execution Adapter
 * 
 * Provides an impressive, real-time autonomous execution stream for hackathon judging,
 * demonstrating KALKI's closed-loop planning, tool use, memory retrieval, test-failure,
 * auto-recovery, deployment, and verification without requiring a live backend.
 */

export class KalkiMockAdapter {
  constructor() {
    this.activeRunId = null;
    this.timer = null;
  }

  /**
   * Generates realistic mock event stream for an objective
   */
  startMockExecution(objective, onEvent, onComplete) {
    this.stop();
    this.activeRunId = 'run-' + Math.random().toString(36).substring(2, 9);
    
    let seq = 1;
    const now = () => new Date().toISOString().substring(11, 19);

    const mockSequence = [
      {
        delay: 400,
        event: {
          type: 'PLAN_CREATED',
          message: 'Created autonomous execution plan with 8 tasks',
          node: 'PLAN',
          data: {
            plan: {
              objective,
              revision: 1,
              tasks: [
                { id: 't-1', description: 'Inspect repository structure & auth module', status: 'pending', tool: 'filesystem' },
                { id: 't-2', description: 'Locate JWT token validation middleware', status: 'pending', tool: 'filesystem' },
                { id: 't-3', description: 'Query engineering memory for callback incidents', status: 'pending', tool: 'memory' },
                { id: 't-4', description: 'Execute unit test suite to reproduce issue', status: 'pending', tool: 'terminal' },
                { id: 't-5', description: 'Apply expiration margin fix to auth middleware', status: 'pending', tool: 'code_edit' },
                { id: 't-6', description: 'Re-run verification & integration tests', status: 'pending', tool: 'terminal' },
                { id: 't-7', description: 'Trigger preview deployment to Vercel', status: 'pending', tool: 'deploy' },
                { id: 't-8', description: 'Perform production smoke test verification', status: 'pending', tool: 'verifier' }
              ]
            }
          }
        }
      },
      {
        delay: 800,
        event: {
          type: 'TASK_STARTED',
          message: 'Task 01: Inspecting repository structure and auth modules',
          node: 'INSPECT',
          data: { task_id: 't-1', tool: 'filesystem' }
        }
      },
      {
        delay: 1200,
        event: {
          type: 'TOOL_STARTED',
          message: 'Executing tool: filesystem.read_dir (path="src/auth")',
          node: 'INSPECT',
          data: { tool: 'filesystem', args: { path: 'src/auth' } }
        }
      },
      {
        delay: 1600,
        event: {
          type: 'TOOL_COMPLETED',
          message: 'Filesystem inspect completed: Found auth.py, middleware.py, profile.py',
          node: 'INSPECT',
          data: { tool: 'filesystem', duration_ms: 180, output: ['auth.py', 'middleware.py', 'profile.py'] }
        }
      },
      {
        delay: 2200,
        event: {
          type: 'MEMORY_RETRIEVED',
          message: 'SIMILAR ENGINEERING INCIDENT FOUND in vector memory (#037)',
          node: 'INSPECT',
          data: {
            memory: {
              incident_id: 'INC-037',
              title: 'Authentication callback token expiration mismatch',
              similarity: 0.91,
              scope: 'long_term',
              previous_resolution: 'Configured clock-skew tolerance window (60s margin) in JWT verify header.',
              decision_impact: 'Applying previous resolution as supporting evidence for fix plan.'
            }
          }
        }
      },
      {
        delay: 3000,
        event: {
          type: 'TEST_STARTED',
          message: 'Running unit test suite: pytest tests/test_auth.py',
          node: 'TEST',
          data: { suite: 'auth_suite', total_tests: 16 }
        }
      },
      {
        delay: 3800,
        event: {
          type: 'TEST_FAILED',
          message: '2 TESTS FAILED: test_token_expiration_skew & test_callback_refresh',
          node: 'DEBUG',
          data: {
            failed_count: 2,
            passed_count: 14,
            failures: [
              'TokenExpiredError: Signature has expired (skew delta: +4s > limit 0s)',
              'CallbackError: Invalid session context during refresh handoff'
            ]
          }
        }
      },
      {
        delay: 4500,
        event: {
          type: 'TOOL_FAILED',
          message: 'Tool terminal.run_test failed: Non-zero exit code (1)',
          node: 'DEBUG',
          data: { tool: 'terminal', failure_class: 'logic_error', error: 'Test suite failure detected' }
        }
      },
      {
        delay: 5200,
        event: {
          type: 'RECOVERY_STARTED',
          message: 'BOUNDED FAILURE RECOVERY ACTIVATED: Categorized failure as LOGIC_ERROR → Triggering dynamic replan',
          node: 'RECOVERING',
          data: {
            recovery_stage: 'DIAGNOSING',
            strategy: 'REPLAN_WITH_MEMORY',
            action: 'Modify middleware.py to add 60s skew tolerance based on INC-037'
          }
        }
      },
      {
        delay: 6000,
        event: {
          type: 'PLAN_REVISED',
          message: 'Plan revised (Revision 2): Adjusted task t-5 parameters with clock-skew fix',
          node: 'RECOVERING',
          data: { revision: 2 }
        }
      },
      {
        delay: 6800,
        event: {
          type: 'CODE_CHANGED',
          message: 'Applied code fix to auth/middleware.py (+14 lines, -4 lines)',
          node: 'CODE',
          data: {
            file: 'src/auth/middleware.py',
            summary: 'Added 60s clock skew tolerance to PyJWT verify context',
            diff: `@@ -42,7 +42,12 @@ def verify_jwt_token(token: str):
-    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
+    payload = jwt.decode(
+        token, 
+        SECRET_KEY, 
+        algorithms=["HS256"],
+        leeway=60  # Added 60s clock-skew margin per INC-037
+    )
     return payload`
          }
        }
      },
      {
        delay: 7800,
        event: {
          type: 'TEST_STARTED',
          message: 'Re-running test suite after recovery patch...',
          node: 'TEST',
          data: { suite: 'auth_suite' }
        }
      },
      {
        delay: 8600,
        event: {
          type: 'TEST_PASSED',
          message: '16 / 16 TESTS PASSED: All authentication unit & integration tests clean! ✓',
          node: 'TEST',
          data: { total: 16, passed: 16, failed: 0 }
        }
      },
      {
        delay: 9400,
        event: {
          type: 'DEPLOY_STARTED',
          message: 'Deploying preview build to Vercel staging environment...',
          node: 'DEPLOY',
          data: { target: 'preview', environment: 'https://kalki-auth-fix.vercel.app' }
        }
      },
      {
        delay: 10200,
        event: {
          type: 'DEPLOY_COMPLETED',
          message: 'Preview deployment live! Build ✓ Health Check ✓ Smoke Test ✓',
          node: 'DEPLOY',
          data: { status: 'live', url: 'https://kalki-auth-fix.vercel.app' }
        }
      },
      {
        delay: 11000,
        event: {
          type: 'VERIFICATION_STARTED',
          message: 'Independent agent verification: Running production HTTP smoke tests...',
          node: 'VERIFY',
          data: { checks: ['health_endpoint', 'token_issue', 'token_refresh', 'skew_boundary'] }
        }
      },
      {
        delay: 11800,
        event: {
          type: 'VERIFICATION_COMPLETED',
          message: 'KALKI VERIFICATION SUCCESS: All 4 production smoke checks verified clean! ✓',
          node: 'VERIFY',
          data: { verified: true, score: 1.0 }
        }
      },
      {
        delay: 12400,
        event: {
          type: 'MEMORY_STORED',
          message: 'Stored resolution experience in long-term engineering memory (INC-084)',
          node: 'LEARN',
          data: { memory_id: 'INC-084', tags: ['auth', 'jwt', 'leeway', 'recovery'] }
        }
      },
      {
        delay: 13000,
        event: {
          type: 'OBJECTIVE_COMPLETED',
          message: 'OBJECTIVE ACCOMPLISHED: Authentication bug fixed, verified, deployed, and learned!',
          node: 'COMPLETED',
          data: { status: 'completed', total_duration_s: 13.0 }
        }
      }
    ];

    let index = 0;
    const scheduleNext = () => {
      if (index >= mockSequence.length) {
        if (onComplete) onComplete({ status: 'completed' });
        return;
      }

      const item = mockSequence[index];
      this.timer = setTimeout(() => {
        const fullEvent = {
          id: `evt-mock-${seq}`,
          seq: seq++,
          task_id: this.activeRunId,
          timestamp: now(),
          ...item.event
        };
        onEvent(fullEvent);
        index++;
        scheduleNext();
      }, index === 0 ? item.delay : item.delay - mockSequence[index - 1].delay);
    };

    scheduleNext();
    return this.activeRunId;
  }

  stop() {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }
}
