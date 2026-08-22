/**
 * KALKI — HERO Live Execution Timeline Component
 */

const EVENT_ICONS = {
  PLAN_CREATED: '📋',
  PLAN_REVISED: '↻',
  TASK_STARTED: '▶',
  TOOL_STARTED: '⚙',
  TOOL_COMPLETED: '✓',
  TOOL_FAILED: '×',
  MEMORY_RETRIEVED: '🧠',
  MEMORY_STORED: '💾',
  CODE_CHANGED: '📝',
  TEST_STARTED: '🧪',
  TEST_FAILED: '⚠️',
  TEST_PASSED: '✓',
  RECOVERY_STARTED: '🛡️',
  DEPLOY_STARTED: '🚀',
  DEPLOY_COMPLETED: '✓',
  VERIFICATION_STARTED: '🔍',
  VERIFICATION_COMPLETED: '🎯',
  APPROVAL_REQUIRED: '🔐',
  OBJECTIVE_COMPLETED: '🏆',
  OBJECTIVE_FAILED: '💥',
  LOG: '💬'
};

export class LiveTimeline {
  constructor(container) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.events = [];
    this.render();
  }

  addEvent(event) {
    this.events.unshift(event); // Newest events top
    this.render();
  }

  clear() {
    this.events = [];
    this.render();
  }

  render() {
    if (this.events.length === 0) {
      this.container.innerHTML = `
        <div class="timeline-panel" style="height: 100%;">
          <div class="panel-header">
            <span>LIVE EXECUTION TIMELINE</span>
            <span class="badge badge-cyan">0 EVENTS</span>
          </div>
          <div class="timeline-stream" style="justify-content: center; align-items: center; text-align: center; color: var(--text-muted);">
            <div style="font-size: 28px; margin-bottom: 8px;">⚡</div>
            <div class="font-mono" style="font-size: 12px; font-weight: 600;">AWAITING OBJECTIVE EXECUTION</div>
            <div style="font-size: 11px; margin-top: 4px;">Click [START KALKI] to stream live agent execution events</div>
          </div>
        </div>
      `;
      return;
    }

    const html = `
      <div class="timeline-panel" style="height: 100%;">
        <div class="panel-header">
          <span>LIVE EXECUTION TIMELINE</span>
          <span class="badge badge-cyan">${this.events.length} EVENTS</span>
        </div>
        <div class="timeline-stream">
          ${this.events.map((evt) => {
            const icon = EVENT_ICONS[evt.type] || '⚡';
            const timeStr = evt.timestamp ? (evt.timestamp.includes('T') ? evt.timestamp.substring(11, 19) : evt.timestamp) : '';
            const typeClass = `type-${evt.type}`;
            const hasData = evt.data && Object.keys(evt.data).length > 0;

            return `
              <div class="timeline-event-card ${typeClass}">
                <div class="event-meta-row">
                  <div style="display: flex; align-items: center; gap: 6px;">
                    <span>${icon}</span>
                    <span class="badge badge-cyan">${evt.type}</span>
                  </div>
                  <span class="event-time">${timeStr}</span>
                </div>
                <div class="event-message">${evt.message}</div>
                ${hasData ? `
                  <details>
                    <summary style="cursor: pointer; font-size: 10px; color: var(--text-muted); margin-top: 4px;">[+] Payload Data</summary>
                    <pre class="event-details-json">${JSON.stringify(evt.data, null, 2)}</pre>
                  </details>
                ` : ''}
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;

    this.container.innerHTML = html;
  }
}
