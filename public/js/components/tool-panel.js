/**
 * KALKI — Tool Activity Panel Component
 */

const TOOLS_LIST = [
  { id: 'filesystem', name: 'FILESYSTEM', icon: '📁', status: 'idle' },
  { id: 'terminal', name: 'TERMINAL', icon: '💻', status: 'idle' },
  { id: 'git', name: 'GIT', icon: '🌿', status: 'idle' },
  { id: 'github', name: 'GITHUB', icon: '🐙', status: 'idle' },
  { id: 'web', name: 'WEB', icon: '🌐', status: 'idle' },
  { id: 'database', name: 'DATABASE', icon: '🗄️', status: 'idle' },
  { id: 'vercel', name: 'VERCEL', icon: '▲', status: 'idle' }
];

export class ToolPanel {
  constructor(container) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.tools = [...TOOLS_LIST];
    this.activeCalls = [];
    this.render();
  }

  setToolActive(toolId, isRunning = true) {
    const t = this.tools.find(item => item.id === toolId || item.name.toLowerCase() === toolId.toLowerCase());
    if (t) {
      t.status = isRunning ? 'active' : 'completed';
      this.render();
    }
  }

  addToolCall(call) {
    this.activeCalls.unshift(call);
    this.setToolActive(call.tool, false);
  }

  reset() {
    this.tools = TOOLS_LIST.map(t => ({ ...t, status: 'idle' }));
    this.activeCalls = [];
    this.render();
  }

  render() {
    const html = `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div class="panel-header" style="background: transparent; padding: 0;">
          <span>REGISTERED AGENT TOOLS</span>
          <span class="badge badge-cyan">${this.tools.length} TOOLS READY</span>
        </div>

        <!-- Tools Grid -->
        <div class="tools-grid">
          ${this.tools.map(t => {
            let statusBadge = `<span class="badge" style="color: var(--text-muted);">READY</span>`;
            if (t.status === 'active') {
              statusBadge = `<span class="badge badge-active">● RUNNING</span>`;
            } else if (t.status === 'completed') {
              statusBadge = `<span class="badge badge-success">✓ OK</span>`;
            }

            return `
              <div class="tool-card ${t.status === 'active' ? 'active' : ''}">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span>${t.icon}</span>
                  <span style="font-weight: 600; font-size: 12px; color: var(--text-primary);">${t.name}</span>
                </div>
                ${statusBadge}
              </div>
            `;
          }).join('')}
        </div>

        <div class="panel-header" style="background: transparent; padding: 0; margin-top: 10px;">
          <span>RECENT TOOL EXECUTIONS</span>
        </div>

        ${this.activeCalls.length === 0 ? `
          <div style="text-align: center; color: var(--text-muted); padding: 20px 0;" class="font-mono">
            No active tool calls recorded yet
          </div>
        ` : `
          <div style="display: flex; flex-direction: column; gap: 8px;">
            ${this.activeCalls.map(c => `
              <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); padding: 10px; border-radius: var(--radius-xs); font-family: var(--font-mono); font-size: 11px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                  <span style="color: var(--accent-cyan); font-weight: 700;">${c.tool}</span>
                  <span class="badge badge-success">${c.duration_ms || 120}ms</span>
                </div>
                <div style="color: var(--text-secondary);">${c.summary || JSON.stringify(c.args || {})}</div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;

    this.container.innerHTML = html;
  }
}
