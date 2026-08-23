/**
 * KALKI — Bounded Failure Recovery Panel
 * Renders the recovery pipeline from RECOVERY_STARTED event data. The stages are
 * KALKI's real recovery model (detect → diagnose → replan → retry → verify); the
 * specifics (failure class, strategy, action) come from the event.
 */

const STAGES = [
  { key: 'detect',   label: 'Failure detected',   icon: '×', field: 'failure' },
  { key: 'diagnose', label: 'Diagnosing root cause', icon: '!', field: 'diagnosis' },
  { key: 'replan',   label: 'Dynamic replanning',  icon: '↻', field: 'strategy' },
  { key: 'retry',    label: 'Alternative action',  icon: '⚙', field: 'action' },
  { key: 'verify',   label: 'Re-verify',           icon: '✓', field: 'verify' },
];

export class RecoveryPanel {
  constructor(container) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.recoveryState = null;
    this.render();
  }

  setRecovery(data) { this.recoveryState = data; this.render(); }
  reset() { this.recoveryState = null; this.render(); }

  render() {
    const r = this.recoveryState;
    if (!r) {
      this.container.innerHTML = `
        <div class="panel-empty">
          <div class="panel-empty-icon">🛡️</div>
          <div class="font-mono panel-empty-title">FAILURE RECOVERY</div>
          <div class="panel-empty-sub">When a step fails, KALKI diagnoses it, replans, and retries — shown here.</div>
        </div>`;
      return;
    }

    const failureClass = r.failure_class || r.failureClass || 'RUNTIME_ERROR';
    const detail = {
      failure: r.failure || r.error || `Categorized as ${failureClass}`,
      diagnosis: r.diagnosis || `${failureClass} → ${r.root_cause || 'analyzing failure signature'}`,
      strategy: r.strategy || 'REPLAN',
      action: r.action || 'Applying alternative approach',
      verify: r.verify || 'Re-running verification after fix',
    };
    const activeStage = r.recovery_stage ? String(r.recovery_stage).toLowerCase() : 'diagnose';
    const activeIdx = STAGES.findIndex(s => activeStage.includes(s.key)) ;

    this.container.innerHTML = `
      <div class="recovery-container">
        <div class="flex-between" style="margin-bottom:4px;">
          <span class="badge badge-failure">× ${failureClass}</span>
          <span class="badge badge-warning">AUTOMATED RECOVERY</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:8px;">
          ${STAGES.map((s, i) => {
            const done = activeIdx >= 0 && i < activeIdx;
            const active = i === activeIdx;
            const border = done ? 'var(--color-success)' : active ? 'var(--accent-cyan)' : 'var(--border-subtle)';
            const badge = done ? '<span class="badge badge-success">DONE</span>'
              : active ? '<span class="badge badge-active">ACTIVE</span>'
              : '<span class="badge" style="color:var(--text-muted);">PENDING</span>';
            return `
              <div class="recovery-step" style="border-left:3px solid ${border};">
                <span style="color:${border};font-weight:700;">${s.icon}</span>
                <div style="flex:1;">
                  <div style="font-weight:600;color:var(--text-primary);">${String(i + 1).padStart(2,'0')} ${s.label}</div>
                  <div style="color:var(--text-muted);font-size:11px;">${detail[s.field]}</div>
                </div>
                ${badge}
              </div>`;
          }).join('')}
        </div>
      </div>`;
  }
}
