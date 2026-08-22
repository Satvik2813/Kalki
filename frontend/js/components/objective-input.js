/**
 * KALKI — Objective Input Bar Component
 * Rendered at the top of the engineering workspace to launch autonomous objectives.
 */

export function renderObjectiveInput(container, options = {}) {
  const html = `
    <div class="objective-card glass-panel mb-3">
      <div class="objective-header-row flex-between mb-2">
        <div class="flex-center gap-2">
          <span class="text-accent font-bold text-xs tracking-wider">⚡ OBJECTIVE DISPATCHER</span>
        </div>
        <div class="text-xs text-muted">Autonomy: <strong class="text-accent">Autonomous (L4)</strong></div>
      </div>
      <div class="objective-input-row">
        <textarea 
          id="objective-text-input" 
          class="objective-input" 
          rows="2"
          placeholder="Describe engineering objective (e.g. Fix authentication token expiration bug, run tests, and verify production)..."
        >Fix authentication token expiration bug, run tests, and verify production.</textarea>
        <button id="start-kalki-btn" class="btn btn-accent btn-large flex-center gap-2">
          <span>START KALKI</span>
          <span>→</span>
        </button>
      </div>
    </div>
  `;

  if (typeof container === 'string') {
    const el = document.querySelector(container);
    if (el) el.innerHTML = html;
  } else if (container) {
    container.innerHTML = html;
  }

  const btnStart = document.getElementById('start-kalki-btn');
  const inputEl = document.getElementById('objective-text-input');

  if (btnStart && inputEl) {
    btnStart.addEventListener('click', () => {
      const val = inputEl.value.trim();
      if (!val) return;
      if (options.onStart) {
        options.onStart(val);
      }
    });

    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        btnStart.click();
      }
    });
  }
}
