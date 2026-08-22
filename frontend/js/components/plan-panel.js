/**
 * KALKI — Execution Plan Panel Component
 */

export class PlanPanel {
  constructor(container) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.plan = null;
    this.render();
  }

  setPlan(plan) {
    this.plan = plan;
    this.render();
  }

  updateTaskStatus(taskId, status) {
    if (!this.plan || !this.plan.tasks) return;
    const task = this.plan.tasks.find(t => t.id === taskId);
    if (task) {
      task.status = status;
      this.render();
    }
  }

  render() {
    if (!this.plan || !this.plan.tasks) {
      this.container.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 40px 0;">
          <div style="font-size: 24px; margin-bottom: 8px;">📋</div>
          <div class="font-mono">NO ACTIVE EXECUTION PLAN</div>
          <div style="font-size: 11px; margin-top: 4px;">Start KALKI to generate an autonomous execution plan</div>
        </div>
      `;
      return;
    }

    const tasks = this.plan.tasks || [];
    const completedCount = tasks.filter(t => t.status === 'completed').length;
    const progressPercent = Math.round((completedCount / tasks.length) * 100) || 0;

    const html = `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div style="display: flex; align-items: center; justify-content: space-between; background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
          <div>
            <div class="font-mono" style="font-size: 11px; color: var(--text-muted);">AUTONOMOUS PLAN (REVISION ${this.plan.revision || 1})</div>
            <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-top: 2px;">${this.plan.objective}</div>
          </div>
          <div class="badge badge-cyan">${completedCount} / ${tasks.length} COMPLETED</div>
        </div>

        <!-- Progress Bar -->
        <div style="height: 4px; background: var(--bg-dark); border-radius: 2px; overflow: hidden;">
          <div style="width: ${progressPercent}%; height: 100%; background: var(--accent-cyan); transition: width 0.3s ease;"></div>
        </div>

        <!-- Task List Tree -->
        <div class="plan-tree">
          ${tasks.map((t, idx) => {
            const isDone = t.status === 'completed';
            const isActive = t.status === 'running' || t.status === 'active';
            const isFailed = t.status === 'failed';
            const isRecovering = t.status === 'recovering';

            let badgeClass = 'badge';
            let statusText = '○ PENDING';

            if (isDone) { badgeClass = 'badge badge-success'; statusText = '✓ COMPLETE'; }
            else if (isActive) { badgeClass = 'badge badge-active'; statusText = '● ACTIVE'; }
            else if (isFailed) { badgeClass = 'badge badge-failure'; statusText = '× FAILED'; }
            else if (isRecovering) { badgeClass = 'badge badge-warning'; statusText = '↻ RECOVERING'; }

            return `
              <div class="plan-item ${isActive ? 'active' : ''}">
                <div class="plan-item-num">0${idx + 1}</div>
                <div class="plan-item-body">
                  <div class="plan-item-title">${t.description}</div>
                  ${t.tool ? `<div class="plan-item-tool">TOOL: ${t.tool}</div>` : ''}
                </div>
                <span class="${badgeClass}">${statusText}</span>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;

    this.container.innerHTML = html;
  }
}
