/**
 * KALKI — Test & Verification Panel
 * Data-driven from TEST_STARTED / TEST_FAILED / TEST_PASSED events. No fake metrics.
 */

export class TestPanel {
  constructor(container) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.testState = null;
    this.render();
  }

  setTestState(data) { this.testState = data; this.render(); }
  reset() { this.testState = null; this.render(); }

  render() {
    const ts = this.testState;
    if (!ts) {
      this.container.innerHTML = `
        <div class="panel-empty">
          <div class="panel-empty-icon">🧪</div>
          <div class="font-mono panel-empty-title">TEST SUITE</div>
          <div class="panel-empty-sub">Unit and integration results render here as KALKI runs tests.</div>
        </div>`;
      return;
    }

    const phase = ts.phase || (ts.failed > 0 ? 'TEST_FAILED' : 'TEST_PASSED');
    const running = phase === 'TEST_STARTED';
    const passed = ts.passed ?? ts.passed_count;
    const failed = ts.failed ?? ts.failed_count;
    const derivedTotal = (passed ?? 0) + (failed ?? 0);
    const total = ts.total ?? ts.total_tests ?? (derivedTotal > 0 ? derivedTotal : undefined);
    const isPassing = phase === 'TEST_PASSED' || (failed === 0 && !running);

    let statusBadge, statusText, color;
    if (running) { statusBadge = 'badge-active'; statusText = '● RUNNING'; color = 'var(--accent-cyan)'; }
    else if (isPassing) { statusBadge = 'badge-success'; statusText = '✓ PASSED'; color = 'var(--color-success)'; }
    else { statusBadge = 'badge-failure'; statusText = '× FAILED'; color = 'var(--color-failure)'; }

    const countStr = (total != null)
      ? `${passed ?? 0} / ${total}`
      : running ? '…' : (passed != null ? String(passed) : '—');

    const failures = Array.isArray(ts.failures) ? ts.failures : [];
    const suite = ts.suite || ts.suite_name || 'test suite';

    this.container.innerHTML = `
      <div style="display:flex;flex-direction:column;gap:16px;">
        <div class="test-summary">
          <div class="test-summary-main">
            <div class="text-muted font-mono" style="font-size:10px;">${suite.toUpperCase()}</div>
            <div class="test-count" style="color:${color};">${countStr}</div>
            <div class="text-muted font-mono" style="font-size:11px;">tests passing</div>
          </div>
          <span class="badge ${statusBadge}">${statusText}</span>
        </div>

        ${failed > 0 ? `<div class="test-fail-count font-mono">${failed} failing</div>` : ''}

        ${failures.length ? `
          <div class="test-failures">
            <div class="font-mono text-muted" style="font-size:10px;margin-bottom:6px;">FAILURE DETAIL</div>
            ${failures.map(f => `<div class="test-failure-line">× ${typeof f === 'string' ? f : (f.message || JSON.stringify(f))}</div>`).join('')}
          </div>` : ''}

        ${running ? `<div class="test-running font-mono text-muted">Executing ${suite}…</div>` : ''}
      </div>`;
  }
}
