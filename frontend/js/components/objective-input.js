/**
 * KALKI — Objective Dispatcher
 * The primary action of the workspace: describe an engineering objective and launch
 * an autonomous run. Example chips populate the input (they are not fake actions).
 */

const EXAMPLES = [
  { label: 'Fix a bug', text: 'Investigate and fix the failing authentication token expiration handling, then run the test suite to confirm.' },
  { label: 'Add a feature', text: 'Add a /health/ready readiness endpoint that verifies the database connection, with tests.' },
  { label: 'Improve tests', text: 'Increase test coverage for the model provider layer, focusing on error and retry paths.' },
  { label: 'Refactor', text: 'Refactor the orchestration loop for readability without changing behavior; keep all tests green.' },
  { label: 'Investigate', text: 'Investigate why runs occasionally hang and report the root cause with evidence.' },
];

export function renderObjectiveInput(container, options = {}) {
  const html = `
    <div class="objective-card">
      <div class="objective-header-row">
        <span class="objective-eyebrow">⚡ ENGINEERING OBJECTIVE</span>
        <span class="objective-ctx-wrap text-xs">Target: <span id="objective-project-ctx"><span class="badge badge-sm badge-info">local</span> <strong>Kalki</strong> · <span class="text-muted">main</span></span></span>
      </div>

      <div class="objective-input-row">
        <textarea id="objective-text-input" class="objective-input" rows="2"
          aria-label="Engineering objective"
          placeholder="What should KALKI build, fix, or improve? (⌘/Ctrl+Enter to start)"></textarea>
        <button id="start-kalki-btn" class="btn btn-accent btn-large objective-start">
          <span>START KALKI</span><span aria-hidden="true">→</span>
        </button>
        <button id="stop-kalki-btn" class="btn btn-outline btn-large objective-stop hidden">
          <span>■ STOP</span>
        </button>
      </div>

      <div class="objective-examples" aria-label="Example objectives">
        <span class="objective-examples-label text-xs text-muted">Try:</span>
        ${EXAMPLES.map(e => `<button class="example-chip" data-text="${e.text.replace(/"/g, '&quot;')}">${e.label}</button>`).join('')}
      </div>
    </div>
  `;

  const target = typeof container === 'string' ? document.querySelector(container) : container;
  if (target) target.innerHTML = html;

  const btnStart = document.getElementById('start-kalki-btn');
  const btnStop = document.getElementById('stop-kalki-btn');
  const inputEl = document.getElementById('objective-text-input');

  btnStart?.addEventListener('click', () => options.onStart?.());
  btnStop?.addEventListener('click', () => options.onStop?.());

  inputEl?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); options.onStart?.(); }
  });

  document.querySelectorAll('.example-chip').forEach(chip => {
    chip.addEventListener('click', () => options.onExample?.(chip.dataset.text));
  });
}
