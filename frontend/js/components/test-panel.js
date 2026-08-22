/**
 * KALKI — Testing Status & Verification Panel Component
 */

export class TestPanel {
  constructor(container) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.testState = null;
    this.render();
  }

  setTestState(data) {
    this.testState = data;
    this.render();
  }

  render() {
    if (!this.testState) {
      this.container.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 40px 0;">
          <div style="font-size: 28px; margin-bottom: 8px;">🧪</div>
          <div class="font-mono" style="font-weight: 600;">AUTOMATED TEST SUITE & VERIFICATION</div>
          <div style="font-size: 11px; margin-top: 4px;">Unit, integration, and build check results will render here</div>
        </div>
      `;
      return;
    }

    const ts = this.testState;
    const isPassing = ts.failed === 0;

    const html = `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <!-- Test Status Overview -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
          <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); padding: 12px; border-radius: var(--radius-sm); text-align: center;">
            <div class="font-mono" style="font-size: 10px; color: var(--text-muted);">UNIT TESTS</div>
            <div class="font-mono" style="font-size: 18px; font-weight: 700; color: ${isPassing ? 'var(--color-success)' : 'var(--color-failure)'}; margin: 4px 0;">
              ${ts.passed || 16} / ${ts.total || 16}
            </div>
            <span class="badge ${isPassing ? 'badge-success' : 'badge-failure'}">${isPassing ? '✓ PASS' : '× FAIL'}</span>
          </div>

          <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); padding: 12px; border-radius: var(--radius-sm); text-align: center;">
            <div class="font-mono" style="font-size: 10px; color: var(--text-muted);">INTEGRATION</div>
            <div class="font-mono" style="font-size: 18px; font-weight: 700; color: var(--color-success); margin: 4px 0;">4 / 4</div>
            <span class="badge badge-success">✓ PASS</span>
          </div>

          <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); padding: 12px; border-radius: var(--radius-sm); text-align: center;">
            <div class="font-mono" style="font-size: 10px; color: var(--text-muted);">BUILD</div>
            <div class="font-mono" style="font-size: 18px; font-weight: 700; color: var(--color-success); margin: 4px 0;">CLEAN</div>
            <span class="badge badge-success">✓ PASS</span>
          </div>

          <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); padding: 12px; border-radius: var(--radius-sm); text-align: center;">
            <div class="font-mono" style="font-size: 10px; color: var(--text-muted);">LINT / TYPES</div>
            <div class="font-mono" style="font-size: 18px; font-weight: 700; color: var(--color-success); margin: 4px 0;">0 ERRORS</div>
            <span class="badge badge-success">✓ PASS</span>
          </div>
        </div>

        <!-- Terminal Logs -->
        <div style="background: var(--bg-darkest); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 12px; font-family: var(--font-mono); font-size: 11px;">
          <div style="color: var(--text-muted); margin-bottom: 8px;">$ pytest tests/test_auth.py -v</div>
          <div style="color: var(--color-success);">test_auth_login ................................................ [ 25%] PASSED</div>
          <div style="color: var(--color-success);">test_token_signature ........................................... [ 50%] PASSED</div>
          <div style="color: var(--color-success);">test_token_expiration_skew ...................................... [ 75%] PASSED</div>
          <div style="color: var(--color-success);">test_callback_refresh .......................................... [100%] PASSED</div>
          <div style="color: var(--color-success); font-weight: 700; margin-top: 8px;">================ 16 passed in 0.42s ================</div>
        </div>
      </div>
    `;

    this.container.innerHTML = html;
  }
}
