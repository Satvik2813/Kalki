/**
 * KALKI — Bounded Failure Recovery Panel Component
 */

export class RecoveryPanel {
  constructor(container) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.recoveryState = null;
    this.render();
  }

  setRecovery(data) {
    this.recoveryState = data;
    this.render();
  }

  render() {
    if (!this.recoveryState) {
      this.container.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 40px 0;">
          <div style="font-size: 28px; margin-bottom: 8px;">🛡️</div>
          <div class="font-mono" style="font-weight: 600;">BOUNDED FAILURE RECOVERY ENGINE</div>
          <div style="font-size: 11px; margin-top: 4px;">Monitors tool execution & automates failure diagnosis and replanning</div>
        </div>
      `;
      return;
    }

    const r = this.recoveryState;

    const html = `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div class="recovery-container">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="badge badge-failure">× TOOL FAILURE DETECTED</span>
              <span class="font-mono" style="font-size: 11px; color: var(--text-secondary);">Failure Class: LOGIC_ERROR</span>
            </div>
            <span class="badge badge-warning">AUTOMATED RECOVERY ACTIVE</span>
          </div>

          <!-- Stepper Chain -->
          <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 8px;">
            <div class="recovery-step" style="border-left: 3px solid var(--color-failure);">
              <span style="color: var(--color-failure); font-weight: 700;">×</span>
              <div style="flex: 1;">
                <div style="font-weight: 600; color: var(--text-primary);">01 TOOL FAILURE</div>
                <div style="color: var(--text-muted); font-size: 11px;">pytest tests/test_auth.py failed (2 assertions failed)</div>
              </div>
              <span class="badge badge-failure">DETECTED</span>
            </div>

            <div class="recovery-step" style="border-left: 3px solid var(--accent-cyan);">
              <span style="color: var(--accent-cyan); font-weight: 700;">!</span>
              <div style="flex: 1;">
                <div style="font-weight: 600; color: var(--text-primary);">02 DIAGNOSING ROOT CAUSE</div>
                <div style="color: var(--text-muted); font-size: 11px;">Categorized as LOGIC_ERROR → Expiration clock-skew mismatch</div>
              </div>
              <span class="badge badge-cyan">DIAGNOSED</span>
            </div>

            <div class="recovery-step" style="border-left: 3px solid var(--color-warning);">
              <span style="color: var(--color-warning); font-weight: 700;">↻</span>
              <div style="flex: 1;">
                <div style="font-weight: 600; color: var(--text-primary);">03 DYNAMIC REPLANNING</div>
                <div style="color: var(--text-muted); font-size: 11px;">Created Plan Revision 2 incorporating Memory INC-037 resolution</div>
              </div>
              <span class="badge badge-warning">REPLANNED</span>
            </div>

            <div class="recovery-step" style="border-left: 3px solid var(--accent-blue);">
              <span style="color: var(--accent-blue); font-weight: 700;">⚙</span>
              <div style="flex: 1;">
                <div style="font-weight: 600; color: var(--text-primary);">04 ALTERNATIVE ACTION EXECUTED</div>
                <div style="color: var(--text-muted); font-size: 11px;">Applied 60s leeway tolerance patch to middleware.py</div>
              </div>
              <span class="badge badge-active">EXECUTED</span>
            </div>

            <div class="recovery-step" style="border-left: 3px solid var(--color-success); background: var(--color-success-bg);">
              <span style="color: var(--color-success); font-weight: 700;">✓</span>
              <div style="flex: 1;">
                <div style="font-weight: 600; color: var(--color-success);">05 RECOVERY SUCCESSFUL</div>
                <div style="color: var(--color-success); font-size: 11px;">All 16 unit & integration tests passed clean!</div>
              </div>
              <span class="badge badge-success">VERIFIED</span>
            </div>
          </div>
        </div>
      </div>
    `;

    this.container.innerHTML = html;
  }
}
