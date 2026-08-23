/**
 * KALKI — Workspace Header & Context Bar
 * The context bar is the single source of truth for the active project/branch/status
 * (updated by app.setActiveProject / updateAgentStatusBadge).
 */
import { renderKalkiWordmark } from '../branding/wordmark.js';

export function renderHeader(container, options = {}) {
  const html = `
    <header class="header-bar">
      <div class="header-left">
        <div id="kalki-wordmark-target" class="kalki-wordmark-container"></div>
        <span class="kalki-subtitle">AUTONOMOUS AI SOFTWARE ENGINEER</span>
      </div>

      <div class="header-right">
        <div class="mode-toggle-group" role="group" aria-label="Execution mode">
          <button id="mode-live-btn" class="mode-btn" aria-pressed="true" title="Run against the live backend">LIVE</button>
          <button id="mode-demo-btn" class="mode-btn" aria-pressed="false" title="Play a scripted demo run (no backend)">DEMO</button>
        </div>

        <div class="badge badge-cyan" style="display:flex;align-items:center;gap:6px;">
          <span id="system-status-dot" class="status-dot"></span>
          <span id="system-status-text">CONNECTING…</span>
        </div>
      </div>
    </header>

    <div class="context-bar">
      <div class="context-item">
        <span class="context-label">PROJECT</span>
        <span id="ctx-project" class="context-val">Kalki</span>
      </div>
      <div class="context-item">
        <span class="context-label">BRANCH</span>
        <span id="ctx-branch" class="context-val">main</span>
      </div>
      <div class="context-item" style="justify-content:flex-end;">
        <span class="context-label">AGENT</span>
        <span id="ctx-agent-status" class="badge badge-active">IDLE</span>
      </div>
    </div>
  `;

  const target = typeof container === 'string' ? document.querySelector(container) : container;
  if (target) target.innerHTML = html;

  renderKalkiWordmark('#kalki-wordmark-target', { height: 24 });

  const liveBtn = document.getElementById('mode-live-btn');
  const demoBtn = document.getElementById('mode-demo-btn');
  if (liveBtn && demoBtn) {
    liveBtn.addEventListener('click', () => options.onModeChange?.('live'));
    demoBtn.addEventListener('click', () => options.onModeChange?.('demo'));
  }
}
