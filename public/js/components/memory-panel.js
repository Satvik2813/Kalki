/**
 * KALKI — Engineering Memory Panel Component
 */

export class MemoryPanel {
  constructor(container) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.memoryData = null;
    this.render();
  }

  setMemory(data) {
    this.memoryData = data;
    this.render();
  }

  render() {
    if (!this.memoryData) {
      this.container.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 40px 0;">
          <div style="font-size: 28px; margin-bottom: 8px;">🧠</div>
          <div class="font-mono" style="font-weight: 600;">VECTOR ENGINEERING MEMORY</div>
          <div style="font-size: 11px; margin-top: 4px;">Long-term experience retrieval will display here during execution</div>
        </div>
      `;
      return;
    }

    const m = this.memoryData;
    const simPercent = Math.round((m.similarity || 0.91) * 100);

    const html = `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div class="memory-card">
          <div class="memory-header">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span>🧠</span>
              <span class="font-mono" style="font-weight: 700; color: var(--accent-purple);">SIMILAR ENGINEERING INCIDENT FOUND</span>
            </div>
            <div class="memory-similarity">${simPercent}% SIMILARITY</div>
          </div>

          <div style="font-family: var(--font-mono); font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">
            ${m.incident_id || 'Incident #052'}: ${m.title || 'Mondrian per-class coverage disparity under class imbalance'}
          </div>

          <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">
            Scope: <span class="badge badge-purple">${m.scope || 'long_term'}</span>
          </div>

          <div style="background: var(--bg-dark); border: 1px solid var(--border-subtle); border-radius: var(--radius-xs); padding: 10px; margin-bottom: 12px;">
            <div class="font-mono" style="font-size: 10px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px;">PREVIOUS RESOLUTION PATTERN</div>
            <div style="font-size: 12px; color: var(--color-success); font-family: var(--font-mono);">${m.previous_resolution}</div>
          </div>

          <div style="background: rgba(0, 240, 255, 0.04); border: 1px solid var(--border-cyan); border-radius: var(--radius-xs); padding: 10px;">
            <div class="font-mono" style="font-size: 10px; color: var(--accent-cyan); text-transform: uppercase; margin-bottom: 4px;">DECISION IMPACT ON CURRENT OBJECTIVE</div>
            <div style="font-size: 12px; color: var(--text-primary);">${m.decision_impact}</div>
          </div>
        </div>

        <!-- Memory Pipeline Diagram -->
        <div style="display: flex; align-items: center; justify-content: space-around; background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); font-family: var(--font-mono); font-size: 11px;">
          <div style="text-align: center;">
            <div style="color: var(--accent-purple);">MEMORY RETRIEVED</div>
            <div style="font-size: 10px; color: var(--text-muted);">INC-037</div>
          </div>
          <span style="color: var(--text-muted);">→</span>
          <div style="text-align: center;">
            <div style="color: var(--accent-cyan);">PATTERN MATCH</div>
            <div style="font-size: 10px; color: var(--text-muted);">${simPercent}% Vector Match</div>
          </div>
          <span style="color: var(--text-muted);">→</span>
          <div style="text-align: center;">
            <div style="color: var(--color-success);">PLAN UPDATED</div>
            <div style="font-size: 10px; color: var(--text-muted);">Skew Leeway Applied</div>
          </div>
        </div>
      </div>
    `;

    this.container.innerHTML = html;
  }
}
