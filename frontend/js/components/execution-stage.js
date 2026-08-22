/**
 * KALKI — Execution Stage Ribbon Component
 */

const STAGES = [
  { id: 'OBJECTIVE', label: 'OBJECTIVE' },
  { id: 'PLAN', label: 'PLAN' },
  { id: 'INSPECT', label: 'INSPECT' },
  { id: 'CODE', label: 'CODE' },
  { id: 'TEST', label: 'TEST' },
  { id: 'DEBUG', label: 'DEBUG' },
  { id: 'RECOVERING', label: 'RECOVER' },
  { id: 'DEPLOY', label: 'DEPLOY' },
  { id: 'VERIFY', label: 'VERIFY' },
  { id: 'LEARN', label: 'LEARN' }
];

export class StageRibbon {
  constructor(container) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.activeStage = 'OBJECTIVE';
    this.completedStages = new Set();
    this.failedStages = new Set();
    this.render();
  }

  setStage(stageId, status = 'active') {
    if (status === 'completed') {
      this.completedStages.add(stageId);
    } else if (status === 'failed') {
      this.failedStages.add(stageId);
    } else {
      this.activeStage = stageId;
    }
    this.render();
  }

  reset() {
    this.activeStage = 'OBJECTIVE';
    this.completedStages.clear();
    this.failedStages.clear();
    this.render();
  }

  render() {
    const html = `
      <div class="stage-ribbon">
        <div class="stage-pipeline">
          ${STAGES.map((s, idx) => {
            const isCompleted = this.completedStages.has(s.id);
            const isFailed = this.failedStages.has(s.id);
            const isActive = this.activeStage === s.id;

            let stateClass = '';
            let icon = `${idx + 1}`;

            if (isCompleted) {
              stateClass = 'completed';
              icon = '✓';
            } else if (isFailed) {
              stateClass = 'failed';
              icon = '×';
            } else if (isActive) {
              stateClass = s.id === 'RECOVERING' ? 'recovering' : 'active';
              icon = s.id === 'RECOVERING' ? '↻' : '●';
            }

            return `
              <div class="stage-step ${stateClass}">
                <span class="stage-icon">${icon}</span>
                <span>${s.label}</span>
              </div>
              ${idx < STAGES.length - 1 ? `<span class="stage-arrow">→</span>` : ''}
            `;
          }).join('')}
        </div>
      </div>
    `;

    this.container.innerHTML = html;
  }
}
