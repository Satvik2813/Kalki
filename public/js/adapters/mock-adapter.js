/**
 * KALKI — Deterministic Mock Execution Adapter (CertiMind demo)
 *
 * Simulates KALKI autonomously fixing a real defect in the CertiMind repo:
 * per-class coverage gap in the Mondrian split-conformal calibrator, then
 * redeploying to Render and verifying the live /predict endpoint.
 */

export class KalkiMockAdapter {
  constructor() {
    this.activeRunId = null;
    this.timer = null;
  }

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
          message: 'Created autonomous execution plan with 8 tasks for CertiMind',
          node: 'PLAN',
          data: {
            plan: {
              objective,
              revision: 1,
              tasks: [
                { id: 't-1', description: 'Inspect CertiMind repo — locate calibration & ensemble modules',    status: 'pending', tool: 'filesystem' },
                { id: 't-2', description: 'Read Mondrian split-conformal calibrator (per-class quantiles)',   status: 'pending', tool: 'filesystem' },
                { id: 't-3', description: 'Query engineering memory for coverage-fairness incidents',         status: 'pending', tool: 'memory' },
                { id: 't-4', description: 'Run coverage evaluation: pytest tests/test_calibration.py',        status: 'pending', tool: 'terminal' },
                { id: 't-5', description: 'Patch Mondrian quantile clamp for Personality-disorder class',     status: 'pending', tool: 'code_edit' },
                { id: 't-6', description: 'Re-run calibration + ensemble tests with 5 random seeds',          status: 'pending', tool: 'terminal' },
                { id: 't-7', description: 'Trigger Render deploy hook & wait for build',                      status: 'pending', tool: 'deploy' },
                { id: 't-8', description: 'Verify /predict endpoint returns Mondrian sets with fixed coverage', status: 'pending', tool: 'verifier' }
              ]
            }
          }
        }
      },
      {
        delay: 800,
        event: {
          type: 'TASK_STARTED',
          message: 'Task 01: Inspecting CertiMind repository structure',
          node: 'INSPECT',
          data: { task_id: 't-1', tool: 'filesystem' }
        }
      },
      {
        delay: 1200,
        event: {
          type: 'TOOL_STARTED',
          message: 'Executing tool: filesystem.read_dir (path="src/calibration")',
          node: 'INSPECT',
          data: { tool: 'filesystem', args: { path: 'src/calibration' } }
        }
      },
      {
        delay: 1600,
        event: {
          type: 'TOOL_COMPLETED',
          message: 'Repo scan complete: mondrian.py, split_conformal.py, ensemble.py, coverage_report.py',
          node: 'INSPECT',
          data: {
            tool: 'filesystem',
            duration_ms: 172,
            output: ['mondrian.py', 'split_conformal.py', 'ensemble.py', 'coverage_report.py']
          }
        }
      },
      {
        delay: 1700,
        event: { type: 'TASK_COMPLETED', message: 'Task 01 complete', node: 'INSPECT', data: { task_id: 't-1' } }
      },
      {
        delay: 1800,
        event: { type: 'TASK_STARTED', message: 'Task 02: Reading Mondrian split-conformal calibrator', node: 'INSPECT', data: { task_id: 't-2', tool: 'filesystem' } }
      },
      {
        delay: 2100,
        event: { type: 'TASK_COMPLETED', message: 'Task 02 complete — per-class quantile logic mapped', node: 'INSPECT', data: { task_id: 't-2' } }
      },
      {
        delay: 2200,
        event: { type: 'TASK_STARTED', message: 'Task 03: Querying engineering memory for coverage-fairness incidents', node: 'INSPECT', data: { task_id: 't-3', tool: 'memory' } }
      },
      {
        delay: 2400,
        event: {
          type: 'MEMORY_RETRIEVED',
          message: 'SIMILAR ENGINEERING INCIDENT FOUND in vector memory (#052)',
          node: 'INSPECT',
          data: {
            memory: {
              incident_id: 'INC-052',
              title: 'Mondrian per-class coverage disparity under class imbalance',
              similarity: 0.93,
              scope: 'long_term',
              previous_resolution: 'Applied minimum-sample floor + Beta-CDF quantile inflation to rare classes; pooled α distributed via Mondrian partition.',
              decision_impact: 'Using prior resolution as blueprint — will inflate the empirical quantile only for classes with support < 200.'
            }
          }
        }
      },
      {
        delay: 2600,
        event: { type: 'TASK_COMPLETED', message: 'Task 03 complete — retrieved INC-052 at 93% similarity', node: 'INSPECT', data: { task_id: 't-3' } }
      },
      {
        delay: 2900,
        event: { type: 'TASK_STARTED', message: 'Task 04: Running calibration evaluation', node: 'TEST', data: { task_id: 't-4', tool: 'terminal' } }
      },
      {
        delay: 3000,
        event: {
          type: 'TEST_STARTED',
          message: 'Running calibration evaluation: pytest tests/test_calibration.py -q',
          node: 'TEST',
          data: { suite: 'calibration_suite', total_tests: 21 }
        }
      },
      {
        delay: 3800,
        event: {
          type: 'TEST_FAILED',
          message: '2 TESTS FAILED: test_mondrian_per_class_coverage & test_rare_class_coverage_floor',
          node: 'DEBUG',
          data: {
            failed_count: 2,
            passed_count: 19,
            failures: [
              'AssertionError: Personality disorder coverage = 0.62, expected ≥ 0.90 (α=0.10)',
              'AssertionError: Bipolar coverage = 0.81, expected ≥ 0.90 (α=0.10)'
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
          data: { tool: 'terminal', failure_class: 'calibration_error', error: 'Mondrian coverage under target for 2 rare classes' }
        }
      },
      {
        delay: 4600,
        event: { type: 'TASK_FAILED', message: 'Task 04 failed — 2 rare-class coverage assertions', node: 'DEBUG', data: { task_id: 't-4' } }
      },
      {
        delay: 5200,
        event: {
          type: 'RECOVERY_STARTED',
          message: 'BOUNDED FAILURE RECOVERY ACTIVATED: Categorized failure as CALIBRATION_ERROR → Triggering dynamic replan',
          node: 'RECOVERING',
          data: {
            recovery_stage: 'DIAGNOSING',
            strategy: 'REPLAN_WITH_MEMORY',
            action: 'Patch src/calibration/mondrian.py — apply Beta-CDF quantile inflation for classes with n_cal < 200 (INC-052 pattern)'
          }
        }
      },
      {
        delay: 6000,
        event: {
          type: 'PLAN_REVISED',
          message: 'Plan revised (Revision 2): Task t-5 parameters updated with per-class quantile-inflation fix',
          node: 'RECOVERING',
          data: { revision: 2 }
        }
      },
      {
        delay: 6600,
        event: { type: 'TASK_STARTED', message: 'Task 05: Patching Mondrian quantile clamp', node: 'CODE', data: { task_id: 't-5', tool: 'code_edit' } }
      },
      {
        delay: 6800,
        event: {
          type: 'CODE_CHANGED',
          message: 'Applied code fix to src/calibration/mondrian.py (+18 lines, -3 lines)',
          node: 'CODE',
          data: {
            file: 'src/calibration/mondrian.py',
            summary: 'Per-class quantile inflation via Beta-CDF for low-support classes; guarantees ≥1-α coverage under imbalance',
            diff: `@@ -47,9 +47,24 @@ class MondrianConformalCalibrator:
-    def quantile(self, scores, alpha):
-        n = len(scores)
-        q_level = np.ceil((n + 1) * (1 - alpha)) / n
-        return np.quantile(scores, min(q_level, 1.0), method="higher")
+    def quantile(self, scores, alpha, class_id=None):
+        n = len(scores)
+        # Finite-sample correction (Vovk 2005)
+        q_level = np.ceil((n + 1) * (1 - alpha)) / n
+        # Per-class inflation for low-support classes (INC-052)
+        if class_id is not None and n < self.MIN_SUPPORT:
+            # Beta-CDF inflation restores nominal coverage under imbalance
+            q_level = beta.ppf(1 - alpha, n - int(alpha * (n + 1)), int(alpha * (n + 1)) + 1)
+            q_level = min(q_level, 1.0)
+        return np.quantile(scores, min(q_level, 1.0), method="higher")`
          }
        }
      },
      {
        delay: 7500,
        event: { type: 'TASK_COMPLETED', message: 'Task 05 complete — Beta-CDF inflation applied', node: 'CODE', data: { task_id: 't-5' } }
      },
      {
        delay: 7700,
        event: { type: 'TASK_STARTED', message: 'Task 06: Re-running calibration suite across 5 seeds', node: 'TEST', data: { task_id: 't-6', tool: 'terminal' } }
      },
      {
        delay: 7800,
        event: {
          type: 'TEST_STARTED',
          message: 'Re-running calibration suite across 5 seeds after recovery patch...',
          node: 'TEST',
          data: { suite: 'calibration_suite' }
        }
      },
      {
        delay: 8600,
        event: {
          type: 'TEST_PASSED',
          message: '21 / 21 TESTS PASSED: All 7 classes at ≥ 0.90 coverage (α=0.10) across 5 seeds ✓',
          node: 'TEST',
          data: { total: 21, passed: 21, failed: 0 }
        }
      },
      {
        delay: 8800,
        event: { type: 'TASK_COMPLETED', message: 'Task 06 complete — coverage restored across seeds', node: 'TEST', data: { task_id: 't-6' } }
      },
      {
        delay: 9200,
        event: { type: 'TASK_STARTED', message: 'Task 07: Triggering Render deploy hook', node: 'DEPLOY', data: { task_id: 't-7', tool: 'deploy' } }
      },
      {
        delay: 9400,
        event: {
          type: 'DEPLOY_STARTED',
          message: 'Triggering Render deploy hook for CertiMind service...',
          node: 'DEPLOY',
          data: { target: 'production', environment: 'https://certimind.onrender.com/' }
        }
      },
      {
        delay: 10200,
        event: {
          type: 'DEPLOY_COMPLETED',
          message: 'Render deployment live! Docker build ✓ Health probe ✓ Cold-start ✓',
          node: 'DEPLOY',
          data: { status: 'live', url: 'https://certimind.onrender.com/' }
        }
      },
      {
        delay: 10400,
        event: { type: 'TASK_COMPLETED', message: 'Task 07 complete — Render deployment live', node: 'DEPLOY', data: { task_id: 't-7' } }
      },
      {
        delay: 10800,
        event: { type: 'TASK_STARTED', message: 'Task 08: Verifying /predict on production', node: 'VERIFY', data: { task_id: 't-8', tool: 'verifier' } }
      },
      {
        delay: 11000,
        event: {
          type: 'VERIFICATION_STARTED',
          message: 'Independent agent verification: probing /predict on production...',
          node: 'VERIFY',
          data: { checks: ['health_endpoint', 'predict_shape', 'mondrian_coverage', 'rare_class_prediction_set'] }
        }
      },
      {
        delay: 11800,
        event: {
          type: 'VERIFICATION_COMPLETED',
          message: 'KALKI VERIFICATION SUCCESS: All 4 production checks verified clean — coverage restored ✓',
          node: 'VERIFY',
          data: { verified: true, score: 1.0 }
        }
      },
      {
        delay: 11900,
        event: { type: 'TASK_COMPLETED', message: 'Task 08 complete — production verified', node: 'VERIFY', data: { task_id: 't-8' } }
      },
      {
        delay: 12400,
        event: {
          type: 'MEMORY_STORED',
          message: 'Stored resolution experience in long-term engineering memory (INC-089)',
          node: 'LEARN',
          data: { memory_id: 'INC-089', tags: ['certimind', 'conformal', 'mondrian', 'coverage', 'imbalance', 'render'] }
        }
      },
      {
        delay: 13000,
        event: {
          type: 'OBJECTIVE_COMPLETED',
          message: 'OBJECTIVE ACCOMPLISHED: CertiMind Mondrian coverage gap fixed, verified live on Render, and learned!',
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
