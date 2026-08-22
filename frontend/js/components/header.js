/**
 * KALKI — Header & Context Bar Component
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
        <div class="mode-toggle-group">
          <button id="mode-live-btn" class="mode-btn">LIVE API</button>
          <button id="mode-demo-btn" class="mode-btn active">DEMO REPLAY</button>
        </div>

        <div class="badge badge-cyan" style="display: flex; align-items: center; gap: 6px;">
          <span id="system-status-dot" class="status-dot active"></span>
          <span id="system-status-text">SYSTEM OPERATIONAL</span>
        </div>
      </div>
    </header>

    <div class="context-bar">
      <div class="context-item">
        <span class="context-label">PROJECT:</span>
        <span id="ctx-project" class="context-val">Satvik2813 / Kalki</span>
      </div>
      <div class="context-item">
        <span class="context-label">BRANCH:</span>
        <span id="ctx-branch" class="context-val">dev/satvik-core</span>
      </div>
      <div class="context-item" style="justify-content: flex-end;">
        <span class="context-label">AGENT STATUS:</span>
        <span id="ctx-agent-status" class="badge badge-active">IDLE</span>
      </div>
    </div>
  `;

  if (typeof container === 'string') {
    document.querySelector(container).innerHTML = html;
  } else {
    container.innerHTML = html;
  }

  // Render SVG Wordmark into target
  renderKalkiWordmark('#kalki-wordmark-target', { height: 26 });

  // Event handlers for mode toggling
  const liveBtn = document.getElementById('mode-live-btn');
  const demoBtn = document.getElementById('mode-demo-btn');

  if (liveBtn && demoBtn) {
    liveBtn.addEventListener('click', () => {
      liveBtn.classList.add('active');
      demoBtn.classList.remove('active');
      if (options.onModeChange) options.onModeChange('live');
    });

    demoBtn.addEventListener('click', () => {
      demoBtn.classList.add('active');
      liveBtn.classList.remove('active');
      if (options.onModeChange) options.onModeChange('demo');
    });
  }
}
