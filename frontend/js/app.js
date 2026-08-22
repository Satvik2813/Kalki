/**
 * KALKI — Main Application Orchestrator & State Coordinator
 */

import { renderHeader } from './components/header.js';
import { renderObjectiveInput } from './components/objective-input.js';
import { StageRibbon } from './components/execution-stage.js';
import { LiveTimeline } from './components/live-timeline.js';
import { PlanPanel } from './components/plan-panel.js';
import { ToolPanel } from './components/tool-panel.js';
import { MemoryPanel } from './components/memory-panel.js';
import { RecoveryPanel } from './components/recovery-panel.js';
import { CodeDiffView } from './components/code-diff.js';
import { TestPanel } from './components/test-panel.js';
import { DeployPanel } from './components/deploy-panel.js';
import { KalkiAPIAdapter } from './adapters/api-adapter.js';
import { KalkiMockAdapter } from './adapters/mock-adapter.js';

class KalkiApp {
  constructor() {
    this.mode = 'live'; // 'demo' | 'live'
    this.api = new KalkiAPIAdapter();
    this.mock = new KalkiMockAdapter();
    this.activeRunId = null;

    this.selectedProjectType = null;
    this.componentsRendered = false;

    this.initNavigation();
    this.initTabRouting();
    this.checkBackendHealth();
  }

  initComponents() {
    // 1. Render Header
    renderHeader('#header-target', {
      onModeChange: (newMode) => {
        this.mode = newMode;
        console.log(`[KALKI UI] Switched execution mode to: ${newMode}`);
      }
    });

    // 2. Render Objective Input
    renderObjectiveInput('#objective-target', {
      onStart: (objective) => this.handleStartObjective(objective)
    });

    // 3. Initialize Stage Ribbon
    this.stageRibbon = new StageRibbon('#stage-target');

    // 4. Initialize Live Timeline
    this.liveTimeline = new LiveTimeline('#timeline-target');

    // 5. Initialize Control Panels
    this.planPanel = new PlanPanel('#tab-plan');
    this.toolPanel = new ToolPanel('#tab-tools');
    this.memoryPanel = new MemoryPanel('#tab-memory');
    this.recoveryPanel = new RecoveryPanel('#tab-recovery');
    this.codeDiffView = new CodeDiffView('#tab-code');
    this.testPanel = new TestPanel('#tab-tests');
    this.deployPanel = new DeployPanel('#tab-deploy', {
      onApprove: (tools) => this.handleApproveGatedAction(tools)
    });
  }

  initTabRouting() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTab = btn.getAttribute('data-tab');

        tabBtns.forEach(b => b.classList.remove('active'));
        tabPanes.forEach(p => p.classList.remove('active'));

        btn.classList.add('active');
        const activePane = document.getElementById(targetTab);
        if (activePane) activePane.classList.add('active');
      });
    });
  }

  async checkBackendHealth() {
    const health = await this.api.checkHealth();
    const statusText = document.getElementById('system-status-text');
    const statusDot = document.getElementById('system-status-dot');

    if (health.status === 'ok') {
      if (statusText) statusText.textContent = 'SYSTEM OPERATIONAL (API)';
      if (statusDot) statusDot.className = 'status-dot success';
    } else {
      if (statusText) statusText.textContent = 'DEMO MODE (BACKEND STANDALONE)';
      if (statusDot) statusDot.className = 'status-dot active';
    }
  }

  handleStartObjective(objective) {
    console.log(`[KALKI] Starting autonomous execution for objective: "${objective}"`);

    // Reset UI states
    this.stageRibbon.reset();
    this.liveTimeline.clear();
    this.toolPanel.reset();
    this.updateAgentStatusBadge('EXECUTING', 'badge-active');

    if (this.mode === 'demo') {
      this.runMockExecution(objective);
    } else {
      this.runLiveAPIExecution(objective);
    }
  }

  runMockExecution(objective) {
    this.activeRunId = this.mock.startMockExecution(
      objective,
      (evt) => this.handleIncomingEvent(evt),
      (res) => {
        console.log('[KALKI] Mock execution finished:', res);
        this.updateAgentStatusBadge('COMPLETED', 'badge-success');
      }
    );
  }

  async runLiveAPIExecution(objective) {
    try {
      const task = await this.api.createTask(objective, { start: true });
      this.activeRunId = task.id;

      this.api.subscribeToEvents(
        task.id,
        (evt) => this.handleIncomingEvent(evt),
        (err) => console.error('SSE Error:', err),
        (res) => this.updateAgentStatusBadge('COMPLETED', 'badge-success')
      );
    } catch (err) {
      console.error('Failed to run live API task:', err);
      // Fallback to demo mode if API fails
      this.runMockExecution(objective);
    }
  }

  handleIncomingEvent(evt) {
    // 1. Add to Live Timeline HERO
    this.liveTimeline.addEvent(evt);

    // 2. Update Stage Ribbon
    if (evt.node) {
      this.stageRibbon.setStage(evt.node, 'active');
    }

    // 3. Process specific event types to update control panels
    switch (evt.type) {
      case 'PLAN_CREATED':
      case 'PLAN_REVISED':
        if (evt.data && evt.data.plan) {
          this.planPanel.setPlan(evt.data.plan);
        }
        break;

      case 'TASK_STARTED':
        if (evt.data && evt.data.task_id) {
          this.planPanel.updateTaskStatus(evt.data.task_id, 'running');
        }
        break;

      case 'TOOL_STARTED':
        if (evt.data && evt.data.tool) {
          this.toolPanel.setToolActive(evt.data.tool, true);
        }
        break;

      case 'TOOL_COMPLETED':
        if (evt.data && evt.data.tool) {
          this.toolPanel.addToolCall({
            tool: evt.data.tool,
            duration_ms: evt.data.duration_ms || 150,
            summary: evt.message
          });
        }
        break;

      case 'MEMORY_RETRIEVED':
        if (evt.data && evt.data.memory) {
          this.memoryPanel.setMemory(evt.data.memory);
        }
        break;

      case 'RECOVERY_STARTED':
        if (evt.data) {
          this.recoveryPanel.setRecovery(evt.data);
          this.stageRibbon.setStage('RECOVERING', 'active');
        }
        break;

      case 'CODE_CHANGED':
        if (evt.data) {
          this.codeDiffView.setDiff(evt.data);
        }
        break;

      case 'TEST_STARTED':
      case 'TEST_FAILED':
      case 'TEST_PASSED':
        if (evt.data) {
          this.testPanel.setTestState(evt.data);
        }
        break;

      case 'DEPLOY_STARTED':
      case 'DEPLOY_COMPLETED':
        if (evt.data) {
          this.deployPanel.setDeployState(evt.data);
        }
        break;

      case 'APPROVAL_REQUIRED':
        if (evt.data && evt.data.tool) {
          this.deployPanel.setApprovalRequired(true, [evt.data.tool]);
          this.updateAgentStatusBadge('AWAITING APPROVAL', 'badge-warning');
        }
        break;

      case 'OBJECTIVE_COMPLETED':
        this.stageRibbon.setStage('LEARN', 'completed');
        this.updateAgentStatusBadge('COMPLETED', 'badge-success');
        break;
    }
  }

  async handleApproveGatedAction(tools) {
    if (this.activeRunId && this.mode === 'live') {
      await this.api.approveTask(this.activeRunId, tools);
      this.deployPanel.setApprovalRequired(false);
      this.updateAgentStatusBadge('EXECUTING', 'badge-active');
    } else {
      this.deployPanel.setApprovalRequired(false);
      this.updateAgentStatusBadge('EXECUTING', 'badge-active');
    }
  }

  updateAgentStatusBadge(text, badgeClass) {
    const badgeEl = document.getElementById('ctx-agent-status');
    if (badgeEl) {
      badgeEl.className = `badge ${badgeClass}`;
      badgeEl.textContent = text;
    }
  }
  initNavigation() {
    const btnEnter = document.getElementById('btn-enter-kalki');
    const btnGuest = document.getElementById('btn-auth-guest');
    const btnBackAuth = document.getElementById('btn-back-auth');
    const btnConfirmProject = document.getElementById('btn-confirm-project');
    const projectOptions = document.querySelectorAll('.project-option');

    const showView = (viewId) => {
      document.querySelectorAll('.view-section').forEach(v => {
        v.classList.remove('active');
        v.classList.add('hidden');
      });
      const view = document.getElementById(viewId);
      if (view) {
        view.classList.remove('hidden');
        view.classList.add('active');
      }
    };

    if (btnEnter) {
      btnEnter.addEventListener('click', () => showView('auth-view'));
    }

    if (btnGuest) {
      btnGuest.addEventListener('click', () => showView('project-view'));
    }

    if (btnBackAuth) {
      btnBackAuth.addEventListener('click', () => showView('auth-view'));
    }

    projectOptions.forEach(opt => {
      opt.addEventListener('click', () => {
        projectOptions.forEach(o => o.classList.remove('selected'));
        opt.classList.add('selected');
        if (btnConfirmProject) btnConfirmProject.disabled = false;
        
        // Save selected project type to state
        this.selectedProjectType = opt.id.replace('opt-', '');
      });
    });

    if (btnConfirmProject) {
      btnConfirmProject.addEventListener('click', () => {
        console.log(`[KALKI UI] Initializing workspace for: ${this.selectedProjectType}`);
        showView('workspace-view');
        // Render components if they weren't rendered yet
        if (!this.componentsRendered) {
          this.initComponents();
          this.componentsRendered = true;
        }
      });
    }
  }
}

// Instantiate application on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.kalkiApp = new KalkiApp();
});
