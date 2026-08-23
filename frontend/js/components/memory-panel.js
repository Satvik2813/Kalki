/**
 * KALKI — Engineering Memory Panel
 * Renders retrieved long-term memory from MEMORY_RETRIEVED event data.
 */

export class MemoryPanel {
  constructor(container) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.memoryData = null;
    this.render();
  }

  setMemory(data) { this.memoryData = data; this.render(); }
  reset() { this.memoryData = null; this.render(); }

  render() {
    const m = this.memoryData;
    if (!m) {
      this.container.innerHTML = `
        <div class="panel-empty">
          <div class="panel-empty-icon">🧠</div>
          <div class="font-mono panel-empty-title">VECTOR ENGINEERING MEMORY</div>
          <div class="panel-empty-sub">Relevant past incidents KALKI retrieves during a run appear here.</div>
        </div>`;
      return;
    }

    const sim = m.similarity != null ? Math.round(m.similarity * 100) : null;
    const id = m.incident_id || m.id || 'memory';

    this.container.innerHTML = `
      <div style="display:flex;flex-direction:column;gap:14px;">
        <div class="memory-card">
          <div class="memory-header">
            <div class="flex-center gap-2">
              <span>🧠</span>
              <span class="font-mono" style="font-weight:700;color:var(--accent-purple);">SIMILAR INCIDENT RETRIEVED</span>
            </div>
            ${sim != null ? `<div class="memory-similarity">${sim}% match</div>` : ''}
          </div>

          <div class="font-mono" style="font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:6px;">
            ${id}${m.title ? `: ${m.title}` : ''}
          </div>
          ${m.scope ? `<div style="font-size:12px;color:var(--text-secondary);margin-bottom:12px;">Scope: <span class="badge badge-purple badge-sm">${m.scope}</span></div>` : ''}

          ${m.previous_resolution ? `
            <div class="memory-block">
              <div class="memory-block-label">PREVIOUS RESOLUTION</div>
              <div class="font-mono" style="font-size:12px;color:var(--color-success);">${m.previous_resolution}</div>
            </div>` : ''}

          ${m.decision_impact ? `
            <div class="memory-block accent">
              <div class="memory-block-label" style="color:var(--accent-cyan);">IMPACT ON CURRENT OBJECTIVE</div>
              <div style="font-size:12px;color:var(--text-primary);">${m.decision_impact}</div>
            </div>` : ''}
        </div>
      </div>`;
  }
}
