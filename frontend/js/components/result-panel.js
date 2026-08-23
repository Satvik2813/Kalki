/**
 * KALKI — Final Result Panel
 * Summarizes the terminal state of a run. Values come from the backend result
 * object and/or the observed event stream — nothing is fabricated.
 */

export class ResultPanel {
  constructor(container, options = {}) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.options = options;
    this.result = null;
    this.context = {};
    this.render();
  }

  setResult(result, context = {}) { this.result = result; this.context = context || {}; this.render(); }
  reset() { this.result = null; this.context = {}; this.render(); }

  _deriveFromEvents(events = []) {
    const byType = t => events.filter(e => e.type === t);
    const changedFiles = [...new Set(byType('CODE_CHANGED').map(e => e.data?.file).filter(Boolean))];
    const lastTest = [...events].reverse().find(e => ['TEST_PASSED', 'TEST_FAILED'].includes(e.type));
    const verified = byType('VERIFICATION_COMPLETED').some(e => e.data?.verified !== false) && byType('VERIFICATION_COMPLETED').length > 0;
    const memoryStored = byType('MEMORY_STORED').map(e => e.data?.memory_id).filter(Boolean);
    const recoveries = byType('RECOVERY_STARTED').length;
    const toolCalls = byType('TOOL_COMPLETED').length;
    return { changedFiles, lastTest, verified, memoryStored, recoveries, toolCalls };
  }

  render() {
    const r = this.result;
    if (!r) {
      this.container.innerHTML = `
        <div class="panel-empty">
          <div class="panel-empty-icon">🎯</div>
          <div class="font-mono panel-empty-title">FINAL RESULT</div>
          <div class="panel-empty-sub">A full summary appears here when the run reaches a terminal state.</div>
        </div>`;
      return;
    }

    const ok = (r.status || '').toLowerCase() === 'completed' || r.success === true;
    const d = this._deriveFromEvents(this.context.events || []);
    const project = this.context.project || {};
    const objective = r.objective || project.objective || '—';

    const stat = (label, value, tone = '') =>
      `<div class="result-stat ${tone}"><div class="result-stat-val">${value}</div><div class="result-stat-label">${label}</div></div>`;

    const testStr = d.lastTest
      ? (d.lastTest.type === 'TEST_PASSED'
          ? `${d.lastTest.data?.passed ?? d.lastTest.data?.total ?? '✓'} passed`
          : `${d.lastTest.data?.failed_count ?? d.lastTest.data?.failed ?? '×'} failing`)
      : '—';

    const header = `
      <div class="result-banner ${ok ? 'ok' : 'fail'}">
        <div class="result-banner-icon">${ok ? '🏆' : '💥'}</div>
        <div>
          <div class="result-banner-title">${ok ? 'Objective accomplished' : 'Objective not completed'}</div>
          <div class="result-banner-obj">${objective}</div>
        </div>
        <span class="badge ${ok ? 'badge-success' : 'badge-failure'}">${(r.status || (ok ? 'completed' : 'failed')).toUpperCase()}</span>
      </div>`;

    const stats = `
      <div class="result-stats">
        ${stat('Files changed', d.changedFiles.length || (r.files_changed?.length ?? 0))}
        ${stat('Tool calls', d.toolCalls)}
        ${stat('Recoveries', d.recoveries, d.recoveries ? 'warn' : '')}
        ${stat('Tests', testStr, ok ? 'ok' : 'fail')}
        ${stat('Verified', d.verified ? 'yes' : (ok ? '—' : 'no'), d.verified ? 'ok' : '')}
        ${stat('Memory', d.memoryStored.length ? 'stored' : '—')}
      </div>`;

    const changed = d.changedFiles.length ? `
      <div class="result-section">
        <div class="result-section-title">Changed files</div>
        <ul class="result-file-list">${d.changedFiles.map(f => `<li class="font-mono">${f}</li>`).join('')}</ul>
      </div>` : '';

    const target = `
      <div class="result-section">
        <div class="result-section-title">Target</div>
        <div class="font-mono result-target">
          <span class="badge badge-sm badge-info">${project.type || 'local'}</span>
          ${project.name || 'Kalki'} · ${project.branch || 'main'}
        </div>
        ${project.url ? `<button class="btn btn-sm btn-outline mt-2" id="result-open-repo">Open repository ↗</button>` : ''}
      </div>`;

    const failInfo = !ok ? `
      <div class="result-section">
        <div class="result-section-title">What failed</div>
        <div class="result-fail-box font-mono">${r.error || r.reason || r.message || 'The run ended without completing the objective.'}</div>
        ${d.recoveries ? `<div class="text-muted text-xs mt-2">KALKI attempted ${d.recoveries} bounded recovery cycle(s) before stopping.</div>` : ''}
        <div class="result-next">Recommended next step: ${r.next_action || 'review the timeline and recovery panel, refine the objective, and re-run.'}</div>
      </div>` : '';

    this.container.innerHTML = `
      <div class="result-wrap">${header}${stats}${changed}${target}${failInfo}</div>`;

    const openBtn = document.getElementById('result-open-repo');
    if (openBtn && this.options.onViewRepo) openBtn.addEventListener('click', () => this.options.onViewRepo(project.url));
  }
}
