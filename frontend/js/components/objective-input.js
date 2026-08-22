/**
 * KALKI — Objective Input Component
 */

export function renderObjectiveInput(container, options = {}) {
  const html = `
    <section class="objective-section">
      <div class="objective-box">
        <input 
          id="objective-text-input" 
          type="text" 
          class="objective-input" 
          placeholder="What engineering objective should KALKI accomplish autonomously?"
          value="Fix authentication token expiration bug, run tests, deploy fix and verify production."
        />
        <div class="objective-actions">
          <button class="preset-btn" data-preset="auth">Presets: Auth Fix</button>
          <button class="preset-btn" data-preset="webhook">Payment Webhook</button>
          <button class="preset-btn" data-preset="memory">Vector Memory</button>

          <button id="start-kalki-btn" class="btn-kalki-primary">
            <span>START KALKI</span>
            <span>→</span>
          </button>
        </div>
      </div>
    </section>
  `;

  if (typeof container === 'string') {
    document.querySelector(container).innerHTML = html;
  } else {
    container.innerHTML = html;
  }

  const inputEl = document.getElementById('objective-text-input');
  const startBtn = document.getElementById('start-kalki-btn');

  // Handle Preset Clicks
  const presets = {
    auth: 'Fix authentication token expiration bug, run tests, deploy fix and verify production.',
    webhook: 'Implement payment webhook handler with exponential retry and zero-drop guarantees.',
    memory: 'Refactor vector memory indexing schema for sub-10ms retrieval latency.'
  };

  document.querySelectorAll('.preset-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const type = e.target.getAttribute('data-preset');
      if (presets[type]) {
        inputEl.value = presets[type];
      }
    });
  });

  // Handle Start Execution
  const triggerStart = () => {
    const val = inputEl.value.trim();
    if (!val) return;
    if (options.onStart) {
      options.onStart(val);
    }
  };

  startBtn.addEventListener('click', triggerStart);
  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') triggerStart();
  });
}
