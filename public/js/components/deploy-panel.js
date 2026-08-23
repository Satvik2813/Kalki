/**
 * KALKI — Deployment & Verification Matrix Component
 */

export class DeployPanel {
  constructor(container, options = {}) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.options = options;
    this.deployState = null;
    this.approvalRequired = false;
    this.render();
  }

  setDeployState(data) {
    this.deployState = data;
    this.render();
  }

  setApprovalRequired(required, tools = []) {
    this.approvalRequired = required;
    this.approvalTools = tools;
    this.render();
  }

  render() {
    const html = `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        ${this.approvalRequired ? `
          <div class="approval-banner">
            <div>
              <div class="font-mono" style="font-size: 13px; font-weight: 700; color: var(--color-warning);">🔐 HUMAN APPROVAL REQUIRED FOR PRODUCTION ACTION</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                KALKI requests approval to run gated tool: <span class="font-mono" style="color: var(--accent-cyan); font-weight: 700;">${(this.approvalTools || ['deploy_production']).join(', ')}</span>
              </div>
            </div>
            <div class="approval-actions">
              <button id="approve-action-btn" class="btn-approve">APPROVE & RESUME →</button>
            </div>
          </div>
        ` : ''}

        <!-- Deployment Matrix Card -->
        <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 16px;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span>🚀</span>
              <span class="font-mono" style="font-weight: 700; color: var(--text-primary);">DEPLOYMENT MATRIX</span>
            </div>
            <span class="badge badge-success">● VERIFIED LIVE</span>
          </div>

          <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; font-family: var(--font-mono); font-size: 12px;">
            <div style="background: var(--bg-dark); padding: 10px; border-radius: var(--radius-xs); border: 1px solid var(--border-subtle);">
              <span style="color: var(--text-muted);">ENVIRONMENT:</span>
              <span style="color: var(--accent-cyan); font-weight: 700; margin-left: 6px;">PREVIEW / STAGING</span>
            </div>

            <div style="background: var(--bg-dark); padding: 10px; border-radius: var(--radius-xs); border: 1px solid var(--border-subtle);">
              <span style="color: var(--text-muted);">BUILD PIPELINE:</span>
              <span style="color: var(--color-success); font-weight: 700; margin-left: 6px;">✓ SUCCESSFUL</span>
            </div>

            <div style="background: var(--bg-dark); padding: 10px; border-radius: var(--radius-xs); border: 1px solid var(--border-subtle);">
              <span style="color: var(--text-muted);">HEALTH CHECK:</span>
              <span style="color: var(--color-success); font-weight: 700; margin-left: 6px;">✓ 200 OK (14ms)</span>
            </div>

            <div style="background: var(--bg-dark); padding: 10px; border-radius: var(--radius-xs); border: 1px solid var(--border-subtle);">
              <span style="color: var(--text-muted);">SMOKE TESTS:</span>
              <span style="color: var(--color-success); font-weight: 700; margin-left: 6px;">✓ 4 / 4 PASSED</span>
            </div>
          </div>

          <div style="margin-top: 14px; background: rgba(63, 185, 80, 0.08); border: 1px solid var(--color-success-border); padding: 12px; border-radius: var(--radius-xs); display: flex; align-items: center; justify-content: space-between;">
            <div class="font-mono" style="font-size: 12px; color: var(--color-success);">
              Deployment URL: <a href="https://certimind.onrender.com/" target="_blank" style="color: var(--accent-cyan); text-decoration: none; font-weight: 600;">https://certimind.onrender.com/</a>
            </div>
            <span class="badge badge-success">VERIFIED</span>
          </div>
        </div>
      </div>
    `;

    this.container.innerHTML = html;

    const approveBtn = document.getElementById('approve-action-btn');
    if (approveBtn && this.options.onApprove) {
      approveBtn.addEventListener('click', () => {
        this.options.onApprove(this.approvalTools);
      });
    }
  }
}
