/**
 * KALKI — Deployment & Approval Panel
 * Fully event-driven: renders only what DEPLOY_* / APPROVAL events actually report.
 * No fabricated metrics.
 */

export class DeployPanel {
  constructor(container, options = {}) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.options = options;
    this.deployState = null;
    this.approvalRequired = false;
    this.approvalTools = [];
    this.render();
  }

  setDeployState(data) { this.deployState = data; this.render(); }
  setApprovalRequired(required, tools = []) { this.approvalRequired = required; this.approvalTools = tools; this.render(); }
  reset() { this.deployState = null; this.approvalRequired = false; this.approvalTools = []; this.render(); }

  render() {
    const d = this.deployState;
    const live = d && (d.status === 'live' || d.phase === 'DEPLOY_COMPLETED');
    const url = d?.url || d?.environment;

    const approval = this.approvalRequired ? `
      <div class="approval-banner">
        <div>
          <div class="font-mono" style="font-size:13px;font-weight:700;color:var(--color-warning);">🔐 Human approval required</div>
          <div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">
            KALKI requests approval to run gated tool:
            <span class="font-mono" style="color:var(--accent-cyan);font-weight:700;">${(this.approvalTools || ['deploy_production']).join(', ')}</span>
          </div>
        </div>
        <div class="approval-actions">
          <button id="approve-action-btn" class="btn-approve">Approve &amp; resume →</button>
        </div>
      </div>` : '';

    let matrix;
    if (!d) {
      matrix = `
        <div class="panel-empty">
          <div class="panel-empty-icon">🚀</div>
          <div class="font-mono panel-empty-title">DEPLOYMENT</div>
          <div class="panel-empty-sub">Deployment status and preview URLs appear here when KALKI ships a build.</div>
        </div>`;
    } else {
      const rows = [
        ['Environment', d.target || d.environment_name || (d.phase === 'DEPLOY_STARTED' ? 'provisioning…' : 'preview')],
        ['Status', d.phase === 'DEPLOY_STARTED' ? 'deploying…' : (d.status || 'complete')],
      ].filter(([, v]) => v);

      matrix = `
        <div class="deploy-card">
          <div class="deploy-card-head">
            <div class="flex-center gap-2"><span>🚀</span><span class="font-mono" style="font-weight:700;">DEPLOYMENT</span></div>
            <span class="badge ${live ? 'badge-success' : 'badge-warning'}">${live ? '● LIVE' : '◐ IN PROGRESS'}</span>
          </div>
          <div class="deploy-grid">
            ${rows.map(([k, v]) => `
              <div class="deploy-cell">
                <span class="text-muted">${k.toUpperCase()}</span>
                <span class="deploy-cell-val">${v}</span>
              </div>`).join('')}
          </div>
          ${url ? `
            <div class="deploy-url">
              <span class="font-mono text-muted">URL</span>
              <a href="${url.startsWith('http') ? url : 'https://' + url}" target="_blank" rel="noopener">${url}</a>
            </div>` : ''}
        </div>`;
    }

    this.container.innerHTML = `<div style="display:flex;flex-direction:column;gap:16px;">${approval}${matrix}</div>`;

    const approveBtn = document.getElementById('approve-action-btn');
    if (approveBtn && this.options.onApprove) {
      approveBtn.addEventListener('click', () => this.options.onApprove(this.approvalTools));
    }
  }
}
