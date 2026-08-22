/**
 * KALKI — Main Application Orchestrator & Workspace Coordinator
 * Manages Developer Identity, Multi-Service Integrations, and Autonomous Execution.
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

    this.activeProject = {
      name: 'Kalki',
      env: 'Local Sandbox',
      branch: 'main',
      type: 'local'
    };
    this.componentsRendered = false;

    this.initUrlParams();
    this.initNavigation();
    this.initTabRouting();
    this.initAccordions();
    this.initAuthAndIntegrations();
    this.checkBackendHealth();
  }

  initUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (token) {
      this.api.setToken(token);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }

  showView(viewId) {
    document.querySelectorAll('.view-section').forEach(v => {
      v.classList.remove('active');
      v.classList.add('hidden');
    });
    const view = document.getElementById(viewId);
    if (view) {
      view.classList.remove('hidden');
      view.classList.add('active');
    }

    if (viewId === 'workspace-view' && !this.componentsRendered) {
      this.initComponents();
      this.componentsRendered = true;
      this.refreshAllIntegrations();
    }
  }

  async initAuthAndIntegrations() {
    const token = this.api.getToken();
    if (token) {
      const me = await this.api.getMe();
      if (me.authenticated && me.user) {
        this.renderUserBadge(me.user);
        this.showView('workspace-view');
        return;
      }
    }
  }

  renderUserBadge(user) {
    const nameEl = document.getElementById('user-name');
    const avatarEl = document.getElementById('user-avatar');
    if (nameEl) nameEl.textContent = user.name || user.email || 'Developer';
    if (avatarEl) {
      if (user.avatar_url) {
        avatarEl.innerHTML = `<img src="${user.avatar_url}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;" />`;
      } else {
        const initials = (user.name || 'DV').slice(0, 2).toUpperCase();
        avatarEl.textContent = initials;
      }
    }
  }

  initComponents() {
    // 1. Render Header
    renderHeader('#header-target', {
      onModeChange: (newMode) => {
        this.mode = newMode;
        console.log(`[KALKI UI] Switched execution mode to: ${newMode}`);
      }
    });

    // 2. Render Onboarding Flow (Login -> Project -> Objective)
    renderObjectiveInput('#onboarding-content', {
      onStart: (objective, project) => this.handleStartObjective(objective, project)
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

    // 6. Setup Integration Event Listeners
    this.setupIntegrationHandlers();
  }

  setupIntegrationHandlers() {
    // GitHub Connect & Disconnect
    const btnConnectGitHub = document.getElementById('btn-connect-github');
    if (btnConnectGitHub) {
      btnConnectGitHub.addEventListener('click', () => {
        window.location.href = '/api/integrations/github/connect';
      });
    }

    const btnDisconnectGitHub = document.getElementById('btn-disconnect-github');
    if (btnDisconnectGitHub) {
      btnDisconnectGitHub.addEventListener('click', async () => {
        await this.api.disconnectGitHub();
        this.refreshGitHubState();
      });
    }

    // Vercel Connect Modal & Disconnect
    const btnOpenVercel = document.getElementById('btn-open-vercel-modal');
    const modalVercel = document.getElementById('vercel-token-modal');
    const btnCloseVercel = document.getElementById('btn-close-vercel-modal');
    const btnSubmitVercel = document.getElementById('btn-submit-vercel-token');
    const inputVercelToken = document.getElementById('vercel-token-input');
    const errVercel = document.getElementById('vercel-modal-error');

    if (btnOpenVercel && modalVercel) {
      btnOpenVercel.addEventListener('click', () => {
        modalVercel.classList.remove('hidden');
        if (inputVercelToken) inputVercelToken.value = '';
        if (errVercel) errVercel.classList.add('hidden');
      });
    }

    if (btnCloseVercel && modalVercel) {
      btnCloseVercel.addEventListener('click', () => modalVercel.classList.add('hidden'));
    }

    if (btnSubmitVercel && inputVercelToken) {
      btnSubmitVercel.addEventListener('click', async () => {
        const tokenVal = inputVercelToken.value.trim();
        if (!tokenVal) return;
        try {
          btnSubmitVercel.disabled = true;
          btnSubmitVercel.textContent = 'Connecting...';
          await this.api.connectVercel(tokenVal);
          modalVercel.classList.add('hidden');
          this.refreshVercelState();
        } catch (err) {
          if (errVercel) {
            errVercel.textContent = err.message;
            errVercel.classList.remove('hidden');
          }
        } finally {
          btnSubmitVercel.disabled = false;
          btnSubmitVercel.textContent = 'Connect Account';
        }
      });
    }

    const btnDisconnectVercel = document.getElementById('btn-disconnect-vercel');
    if (btnDisconnectVercel) {
      btnDisconnectVercel.addEventListener('click', async () => {
        await this.api.disconnectVercel();
        this.refreshVercelState();
      });
    }

    // Local Pair Button
    const btnPairLocal = document.getElementById('btn-pair-local');
    if (btnPairLocal) {
      btnPairLocal.addEventListener('click', async () => {
        await this.api.connectLocal({
          name: 'Kalki Workspace',
          path: '.',
          git_remote: 'https://github.com/Satvik2813/Kalki.git',
          current_branch: 'integration/kalki-e2e',
          status: 'connected'
        });
        this.refreshLocalState();
      });
    }

    // Logout
    const btnLogout = document.getElementById('btn-logout');
    if (btnLogout) {
      btnLogout.addEventListener('click', () => {
        this.api.clearToken();
        this.showView('landing-view');
      });
    }
  }

  initAccordions() {
    document.querySelectorAll('.integration-header').forEach(header => {
      header.addEventListener('click', () => {
        const section = header.closest('.integration-section');
        if (section) {
          section.classList.toggle('open');
        }
      });
    });
  }

  async refreshAllIntegrations() {
    await Promise.allSettled([
      this.refreshGitHubState(),
      this.refreshVercelState(),
      this.refreshLocalState(),
    ]);
  }

  async refreshGitHubState() {
    const status = await this.api.getGitHubStatus();
    const dot = document.getElementById('github-status-dot');
    const connectBox = document.getElementById('github-connect-box');
    const connectedBox = document.getElementById('github-connected-box');
    const userLabel = document.getElementById('github-user-label');
    const reposList = document.getElementById('github-repos-list');

    if (status.connected) {
      if (dot) dot.className = 'status-dot success';
      if (connectBox) connectBox.classList.add('hidden');
      if (connectedBox) connectedBox.classList.remove('hidden');
      if (userLabel) userLabel.textContent = `@${status.username}`;

      try {
        const data = await this.api.getGitHubRepos();
        if (reposList) {
          reposList.innerHTML = '';
          if (!data.repos || data.repos.length === 0) {
            reposList.innerHTML = '<div class="text-xs text-muted p-2">No repositories found</div>';
          } else {
            data.repos.forEach(repo => {
              const el = document.createElement('div');
              el.className = 'sidebar-item';
              el.innerHTML = `
                <span class="item-name" title="${repo.full_name}">${repo.name}</span>
                <span class="badge badge-sm">${repo.default_branch || 'main'}</span>
              `;
              el.addEventListener('click', () => {
                this.setActiveProject({
                  name: repo.full_name,
                  env: 'GitHub Remote',
                  branch: repo.default_branch || 'main',
                  type: 'github'
                });
                document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
                el.classList.add('active');
              });
              reposList.appendChild(el);
            });
          }
        }
      } catch (err) {
        if (reposList) reposList.innerHTML = `<div class="text-xs text-danger p-2">${err.message}</div>`;
      }
    } else {
      if (dot) dot.className = 'status-dot';
      if (connectBox) connectBox.classList.remove('hidden');
      if (connectedBox) connectedBox.classList.add('hidden');
    }
  }

  async refreshVercelState() {
    const status = await this.api.getVercelStatus();
    const dot = document.getElementById('vercel-status-dot');
    const connectBox = document.getElementById('vercel-connect-box');
    const connectedBox = document.getElementById('vercel-connected-box');
    const userLabel = document.getElementById('vercel-user-label');
    const projectsList = document.getElementById('vercel-projects-list');

    if (status.connected) {
      if (dot) dot.className = 'status-dot success';
      if (connectBox) connectBox.classList.add('hidden');
      if (connectedBox) connectedBox.classList.remove('hidden');
      if (userLabel) userLabel.textContent = `@${status.username}`;

      try {
        const data = await this.api.getVercelProjects();
        if (projectsList) {
          projectsList.innerHTML = '';
          if (!data.projects || data.projects.length === 0) {
            projectsList.innerHTML = '<div class="text-xs text-muted p-2">No Vercel projects found</div>';
          } else {
            data.projects.forEach(proj => {
              const el = document.createElement('div');
              el.className = 'sidebar-item';
              const state = proj.latest_deployment?.readyState || 'READY';
              const stateClass = state === 'READY' ? 'badge-success' : 'badge-warning';
              el.innerHTML = `
                <span class="item-name" title="${proj.name}">${proj.name}</span>
                <span class="badge badge-sm ${stateClass}">${state.toLowerCase()}</span>
              `;
              el.addEventListener('click', () => {
                this.setActiveProject({
                  name: proj.name,
                  env: 'Vercel Cloud',
                  branch: 'production',
                  type: 'vercel'
                });
                document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
                el.classList.add('active');
              });
              projectsList.appendChild(el);
            });
          }
        }
      } catch (err) {
        if (projectsList) projectsList.innerHTML = `<div class="text-xs text-danger p-2">${err.message}</div>`;
      }
    } else {
      if (dot) dot.className = 'status-dot';
      if (connectBox) connectBox.classList.remove('hidden');
      if (connectedBox) connectedBox.classList.add('hidden');
    }
  }

  async refreshLocalState() {
    const dot = document.getElementById('local-status-dot');
    const list = document.getElementById('local-projects-list');
    try {
      const data = await this.api.getLocalProjects();
      if (dot) dot.className = 'status-dot success';
      if (list && data.projects && data.projects.length > 0) {
        list.innerHTML = '';
        data.projects.forEach(p => {
          const el = document.createElement('div');
          el.className = 'sidebar-item';
          el.innerHTML = `
            <span class="item-name" title="${p.local_path}">📁 ${p.name}</span>
            <span class="badge badge-sm badge-info">${p.current_branch}</span>
          `;
          el.addEventListener('click', () => {
            this.setActiveProject({
              name: p.name,
              env: 'Local Workspace',
              branch: p.current_branch,
              type: 'local'
            });
            document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
            el.classList.add('active');
          });
          list.appendChild(el);
        });
      }
    } catch {
      if (dot) dot.className = 'status-dot';
    }
  }

  setActiveProject(project) {
    this.activeProject = project;
    const nameEl = document.getElementById('active-project-name');
    const badgeEl = document.getElementById('active-project-badge');
    const envLabel = document.getElementById('active-env-label');
    const branchName = document.getElementById('active-branch-name');

    if (nameEl) nameEl.textContent = project.name;
    if (badgeEl) {
      badgeEl.textContent = project.type;
      badgeEl.className = `badge badge-sm ${project.type === 'github' ? 'badge-active' : project.type === 'vercel' ? 'badge-success' : 'badge-info'}`;
    }
    if (envLabel) envLabel.textContent = project.env;
    if (branchName) branchName.textContent = project.branch;
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

  handleStartObjective(objective, project) {
    const targetProject = project || this.activeProject?.name || 'Kalki';
    console.log(`[KALKI] Starting autonomous execution for objective: "${objective}" on project "${targetProject}"`);

    // Reset UI states
    this.stageRibbon.reset();
    this.liveTimeline.clear();
    this.toolPanel.reset();
    this.updateAgentStatusBadge('EXECUTING', 'badge-active');

    if (this.mode === 'demo') {
      this.runMockExecution(objective, targetProject);
    } else {
      this.runLiveAPIExecution(objective, targetProject);
    }
  }

  runMockExecution(objective, project) {
    this.activeRunId = this.mock.startMockExecution(
      objective,
      (evt) => this.handleIncomingEvent(evt),
      (res) => {
        console.log('[KALKI] Mock execution finished:', res);
        this.updateAgentStatusBadge('COMPLETED', 'badge-success');
      }
    );
  }

  async runLiveAPIExecution(objective, project) {
    try {
      const targetProject = project || this.activeProject?.name || 'Kalki';
      const task = await this.api.createTask(objective, {
        project: targetProject,
        start: true
      });
      this.activeRunId = task.id;

      this.api.subscribeToEvents(
        task.id,
        (evt) => this.handleIncomingEvent(evt),
        (err) => console.error('SSE Error:', err),
        (res) => this.updateAgentStatusBadge('COMPLETED', 'badge-success')
      );
    } catch (err) {
      console.error('Failed to run live API task:', err);
      this.runMockExecution(objective);
    }
  }

  handleIncomingEvent(evt) {
    this.liveTimeline.addEvent(evt);

    if (evt.node) {
      this.stageRibbon.setStage(evt.node, 'active');
    }

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

    if (btnEnter) {
      btnEnter.addEventListener('click', () => this.showView('auth-view'));
    }

    const btnSkipLanding = document.getElementById('btn-skip-landing');
    if (btnSkipLanding) {
      btnSkipLanding.addEventListener('click', () => {
        this.renderUserBadge({ name: 'Guest Developer (Local)', email: 'guest@local' });
        this.showView('workspace-view');
      });
    }

    const btnAuthSkip = document.getElementById('btn-auth-skip');
    if (btnAuthSkip) {
      btnAuthSkip.addEventListener('click', () => {
        this.renderUserBadge({ name: 'Guest Developer (Local)', email: 'guest@local' });
        this.showView('workspace-view');
      });
    }

    if (btnGuest) {
      btnGuest.addEventListener('click', async () => {
        try {
          const res = await this.api.loginGuest();
          if (res.user) this.renderUserBadge(res.user);
        } catch {
          this.renderUserBadge({ name: 'Guest Developer (Local)', email: 'guest@local' });
        }
        this.showView('project-view');
      });
    }

    if (btnBackAuth) {
      btnBackAuth.addEventListener('click', () => this.showView('auth-view'));
    }

    if (btnConfirmProject) {
      btnConfirmProject.addEventListener('click', () => {
        this.showView('workspace-view');
      });
    }
  }
}

// Instantiate application on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.kalkiApp = new KalkiApp();
});
