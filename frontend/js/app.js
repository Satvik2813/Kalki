/**
 * KALKI — Application Orchestrator
 * Journey: Landing → Auth (Google) → Project selection → Workspace → Live run → Result.
 * Authenticated users only. No guest / anonymous paths.
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
import { ResultPanel } from './components/result-panel.js';
import { renderKalkiWordmark } from './branding/wordmark.js';
import { KalkiAPIAdapter } from './adapters/api-adapter.js';
import { KalkiMockAdapter } from './adapters/mock-adapter.js';

class KalkiApp {
  constructor() {
    this.mode = 'live';               // 'live' | 'demo'
    this.api = new KalkiAPIAdapter();
    this.mock = new KalkiMockAdapter();
    this.activeRunId = null;
    this.isRunning = false;
    this.unsubscribe = null;
    this.authenticated = false;
    this.selectedSource = null;
    this.selectedTarget = null;       // chosen project before entering workspace

    this.activeProject = { name: 'Kalki', env: 'Local Sandbox', branch: 'main', type: 'local' };
    this.componentsRendered = false;

    this.renderBrandLogos();
    this.initUrlParams();
    this.initNavigation();
    this.initProjectSelection();
    this.initTabRouting();
    this.initAccordions();
    this.initComponents();
    this.setupIntegrationHandlers();
    this.checkBackendHealth();
    this.bootAuth();
  }

  // ── Branding ───────────────────────────────────────────────────
  renderBrandLogos() {
    renderKalkiWordmark('#landing-logo', { height: 56 });
    renderKalkiWordmark('#auth-logo', { height: 40 });
    renderKalkiWordmark('#sidebar-logo', { height: 26 });
  }

  // ── URL params / OAuth returns ─────────────────────────────────
  initUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (token) this.api.setToken(token);

    if (params.get('demo') === '1') this.setMode('demo');

    const authError = params.get('auth_error');
    if (authError) {
      const el = document.getElementById('auth-error');
      if (el) {
        el.textContent = `Sign-in failed: ${authError.replace(/_/g, ' ')}`;
        el.classList.remove('hidden');
      }
    }
    this._loginSuccess = params.get('login') === 'success';
    this._integrationReturn = params.get('integration'); // e.g. 'github'

    // Clean the URL
    if (token || authError || params.get('login') || params.get('integration')) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }

  // ── Auth-aware boot ────────────────────────────────────────────
  async bootAuth() {
    const token = this.api.getToken();
    if (token) {
      const me = await this.api.getMe();
      if (me.authenticated && me.user) {
        this.authenticated = true;
        this.renderUserBadge(me.user);
        await this.refreshAllIntegrations();
        // Returning from an integration OAuth → go straight to project picker.
        if (this._integrationReturn) {
          this.showView('project-view');
          this.selectSource(this._integrationReturn);
          return;
        }
        this.showView(this._loginSuccess ? 'project-view' : 'project-view');
        return;
      }
    }
    this.showView('landing-view');
  }

  // ── View switching ─────────────────────────────────────────────
  showView(viewId) {
    document.querySelectorAll('.view-section').forEach(v => {
      v.classList.remove('active');
      v.classList.add('hidden');
    });
    const view = document.getElementById(viewId);
    if (view) { view.classList.remove('hidden'); view.classList.add('active'); }
    this.currentView = viewId;
  }

  renderUserBadge(user) {
    const nameEl = document.getElementById('user-name');
    const avatarEl = document.getElementById('user-avatar');
    if (nameEl) nameEl.textContent = user.name || user.email || 'Developer';
    if (avatarEl) {
      if (user.avatar_url) {
        avatarEl.innerHTML = `<img src="${user.avatar_url}" alt="" style="width:100%;height:100%;border-radius:50%;object-fit:cover;" />`;
      } else {
        avatarEl.textContent = (user.name || 'DV').slice(0, 2).toUpperCase();
      }
    }
  }

  // ── Components ─────────────────────────────────────────────────
  initComponents() {
    if (this.componentsRendered) return;
    this.componentsRendered = true;

    renderHeader('#header-target', {
      onModeChange: (m) => this.setMode(m),
    });

    renderObjectiveInput('#objective-target', {
      onStart: () => this.handleStartObjective(),
      onStop: () => this.handleStopRun(),
      onExample: (text) => this.setObjectiveText(text),
    });

    this.stageRibbon = new StageRibbon('#stage-target');
    this.liveTimeline = new LiveTimeline('#timeline-target');
    this.planPanel = new PlanPanel('#tab-plan');
    this.toolPanel = new ToolPanel('#tab-tools');
    this.memoryPanel = new MemoryPanel('#tab-memory');
    this.recoveryPanel = new RecoveryPanel('#tab-recovery');
    this.codeDiffView = new CodeDiffView('#tab-code');
    this.testPanel = new TestPanel('#tab-tests');
    this.deployPanel = new DeployPanel('#tab-deploy', {
      onApprove: (tools) => this.handleApproveGatedAction(tools),
    });
    this.resultPanel = new ResultPanel('#tab-result', {
      onViewRepo: (url) => window.open(url, '_blank', 'noopener'),
    });

    // Reflect starting mode on the header toggle.
    this.setMode(this.mode, { silent: true });
  }

  setMode(mode, { silent = false } = {}) {
    this.mode = mode;
    const liveBtn = document.getElementById('mode-live-btn');
    const demoBtn = document.getElementById('mode-demo-btn');
    if (liveBtn && demoBtn) {
      liveBtn.classList.toggle('active', mode === 'live');
      liveBtn.setAttribute('aria-pressed', String(mode === 'live'));
      demoBtn.classList.toggle('active', mode === 'demo');
      demoBtn.setAttribute('aria-pressed', String(mode === 'demo'));
    }
    if (!silent) console.log(`[KALKI] mode → ${mode}`);
  }

  // ── Navigation ─────────────────────────────────────────────────
  initNavigation() {
    const on = (id, ev, fn) => { const el = document.getElementById(id); if (el) el.addEventListener(ev, fn); };

    on('btn-enter-kalki', 'click', () => {
      // Already signed in? skip straight to project selection.
      if (this.authenticated) this.showView('project-view');
      else this.showView('auth-view');
    });
    on('btn-back-landing', 'click', () => this.showView('landing-view'));
    on('btn-back-auth', 'click', () => this.showView('auth-view'));

    on('btn-logout', 'click', () => {
      this.api.clearToken();
      this.authenticated = false;
      this.showView('landing-view');
    });

    on('btn-confirm-project', 'click', () => {
      if (!this.selectedTarget) return;
      this.setActiveProject(this.selectedTarget);
      this.showView('workspace-view');
    });
  }

  // ── Project selection screen ───────────────────────────────────
  initProjectSelection() {
    document.querySelectorAll('.project-source-card').forEach(card => {
      card.addEventListener('click', () => this.selectSource(card.dataset.source));
    });
  }

  selectSource(source) {
    this.selectedSource = source;
    document.querySelectorAll('.project-source-card').forEach(c => {
      const on = c.dataset.source === source;
      c.classList.toggle('selected', on);
      c.setAttribute('aria-pressed', String(on));
    });
    this.renderPicker(source);
  }

  async renderPicker(source) {
    const body = document.getElementById('project-picker-body');
    if (!body) return;
    body.innerHTML = `<div class="picker-empty text-muted">Loading ${source}…</div>`;

    if (source === 'github') {
      const status = await this.api.getGitHubStatus();
      if (!status.connected) {
        body.innerHTML = `
          <div class="picker-connect">
            <p class="text-muted">Connect your GitHub account to browse repositories.</p>
            <button class="btn btn-accent" id="picker-connect-github">Connect GitHub</button>
          </div>`;
        document.getElementById('picker-connect-github')
          ?.addEventListener('click', () => { window.location.href = '/api/integrations/github/connect'; });
        return;
      }
      const data = await this.api.getGitHubRepos().catch(e => ({ error: e.message }));
      if (data.error) { body.innerHTML = `<div class="picker-empty text-danger">${data.error}</div>`; return; }
      this.renderPickerList(body, (data.repos || []).map(r => ({
        title: r.full_name, meta: r.default_branch || 'main', desc: r.description || r.language || '',
        target: { name: r.full_name, env: 'GitHub Remote', branch: r.default_branch || 'main', type: 'github', url: r.html_url },
      })), 'No repositories found.');
    }

    else if (source === 'vercel') {
      const status = await this.api.getVercelStatus();
      if (!status.connected) {
        body.innerHTML = `
          <div class="picker-connect">
            <p class="text-muted">Connect Vercel to browse deployed projects.</p>
            <button class="btn btn-accent" id="picker-connect-vercel">Connect Vercel</button>
          </div>`;
        document.getElementById('picker-connect-vercel')
          ?.addEventListener('click', () => this.openVercelModal());
        return;
      }
      const data = await this.api.getVercelProjects().catch(e => ({ error: e.message }));
      if (data.error) { body.innerHTML = `<div class="picker-empty text-danger">${data.error}</div>`; return; }
      this.renderPickerList(body, (data.projects || []).map(p => ({
        title: p.name, meta: (p.latest_deployment?.readyState || 'ready').toLowerCase(),
        desc: p.framework || '',
        target: { name: p.name, env: 'Vercel Cloud', branch: 'production', type: 'vercel' },
      })), 'No Vercel projects found.');
    }

    else { // local
      const data = await this.api.getLocalProjects().catch(() => ({ projects: [] }));
      const items = (data.projects || []).map(p => ({
        title: p.name, meta: p.current_branch || 'main', desc: p.local_path || '',
        target: { name: p.name, env: 'Local Workspace', branch: p.current_branch || 'main', type: 'local' },
      }));
      if (items.length === 0) {
        items.push({
          title: 'Kalki (current workspace)', meta: 'main', desc: 'The repository KALKI is running from.',
          target: { name: 'Kalki', env: 'Local Sandbox', branch: 'main', type: 'local' },
        });
      }
      this.renderPickerList(body, items, 'No local projects paired.');
    }
  }

  renderPickerList(body, items, emptyMsg) {
    if (!items.length) { body.innerHTML = `<div class="picker-empty text-muted">${emptyMsg}</div>`; return; }
    body.innerHTML = `<div class="picker-list"></div>`;
    const list = body.querySelector('.picker-list');
    items.forEach(item => {
      const el = document.createElement('button');
      el.className = 'picker-item';
      el.innerHTML = `
        <span class="picker-item-main">
          <span class="picker-item-title">${item.title}</span>
          ${item.desc ? `<span class="picker-item-desc">${item.desc}</span>` : ''}
        </span>
        <span class="badge badge-sm badge-info">${item.meta}</span>`;
      el.addEventListener('click', () => {
        list.querySelectorAll('.picker-item').forEach(i => i.classList.remove('active'));
        el.classList.add('active');
        this.selectedTarget = item.target;
        const label = document.getElementById('selected-project-label');
        if (label) label.textContent = `${item.target.type} · ${item.target.name}`;
        const confirm = document.getElementById('btn-confirm-project');
        if (confirm) confirm.disabled = false;
      });
      list.appendChild(el);
    });
  }

  // ── Integrations (sidebar) ─────────────────────────────────────
  setupIntegrationHandlers() {
    const on = (id, ev, fn) => { const el = document.getElementById(id); if (el) el.addEventListener(ev, fn); };

    on('btn-connect-github', 'click', () => { window.location.href = '/api/integrations/github/connect'; });
    on('btn-disconnect-github', 'click', async () => { await this.api.disconnectGitHub(); this.refreshGitHubState(); });

    on('btn-open-vercel-modal', 'click', () => this.openVercelModal());
    on('btn-close-vercel-modal', 'click', () => this.closeVercelModal());
    on('btn-submit-vercel-token', 'click', () => this.submitVercelToken());
    on('btn-disconnect-vercel', 'click', async () => { await this.api.disconnectVercel(); this.refreshVercelState(); });

    on('btn-pair-local', 'click', async () => {
      await this.api.connectLocal({
        name: 'Kalki', path: '.', git_remote: '',
        current_branch: this.activeProject.branch || 'main', status: 'connected',
      });
      this.refreshLocalState();
    });
  }

  openVercelModal() {
    const modal = document.getElementById('vercel-token-modal');
    const input = document.getElementById('vercel-token-input');
    const err = document.getElementById('vercel-modal-error');
    if (modal) modal.classList.remove('hidden');
    if (input) { input.value = ''; input.focus(); }
    if (err) err.classList.add('hidden');
  }
  closeVercelModal() {
    document.getElementById('vercel-token-modal')?.classList.add('hidden');
  }
  async submitVercelToken() {
    const input = document.getElementById('vercel-token-input');
    const err = document.getElementById('vercel-modal-error');
    const btn = document.getElementById('btn-submit-vercel-token');
    const val = (input?.value || '').trim();
    if (!val) return;
    try {
      btn.disabled = true; btn.textContent = 'Connecting…';
      await this.api.connectVercel(val);
      this.closeVercelModal();
      this.refreshVercelState();
      if (this.currentView === 'project-view' && this.selectedSource === 'vercel') this.renderPicker('vercel');
    } catch (e) {
      if (err) { err.textContent = e.message; err.classList.remove('hidden'); }
    } finally {
      btn.disabled = false; btn.textContent = 'Connect account';
    }
  }

  initAccordions() {
    document.querySelectorAll('.integration-header').forEach(header => {
      const toggle = () => {
        const section = header.closest('.integration-section');
        if (section) {
          section.classList.toggle('open');
          header.setAttribute('aria-expanded', String(section.classList.contains('open')));
        }
      };
      header.addEventListener('click', toggle);
      header.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
      });
    });
  }

  async refreshAllIntegrations() {
    await Promise.allSettled([this.refreshGitHubState(), this.refreshVercelState(), this.refreshLocalState()]);
    this.refreshSourceCards();
  }

  refreshSourceCards() {
    const set = (dot, state, connected, label) => {
      const d = document.getElementById(dot), s = document.getElementById(state);
      if (d) d.className = `status-dot ${connected ? 'success' : ''}`;
      if (s) { s.textContent = label; s.classList.toggle('connected', connected); }
    };
    this.api.getGitHubStatus().then(st => set('src-github-dot', 'src-github-state', st.connected, st.connected ? `@${st.username}` : 'Not connected'));
    this.api.getVercelStatus().then(st => set('src-vercel-dot', 'src-vercel-state', st.connected, st.connected ? `@${st.username}` : 'Not connected'));
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
      connectBox?.classList.add('hidden');
      connectedBox?.classList.remove('hidden');
      if (userLabel) userLabel.textContent = `@${status.username}`;
      try {
        const data = await this.api.getGitHubRepos();
        if (reposList) {
          reposList.innerHTML = '';
          if (!data.repos?.length) {
            reposList.innerHTML = '<div class="text-xs text-muted p-2">No repositories found</div>';
          } else {
            data.repos.forEach(repo => this.addSidebarItem(reposList, repo.name, repo.default_branch || 'main', repo.full_name, {
              name: repo.full_name, env: 'GitHub Remote', branch: repo.default_branch || 'main', type: 'github', url: repo.html_url,
            }));
          }
        }
      } catch (err) {
        if (reposList) reposList.innerHTML = `<div class="text-xs text-danger p-2">${err.message}</div>`;
      }
    } else {
      if (dot) dot.className = 'status-dot';
      connectBox?.classList.remove('hidden');
      connectedBox?.classList.add('hidden');
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
      connectBox?.classList.add('hidden');
      connectedBox?.classList.remove('hidden');
      if (userLabel) userLabel.textContent = `@${status.username}`;
      try {
        const data = await this.api.getVercelProjects();
        if (projectsList) {
          projectsList.innerHTML = '';
          if (!data.projects?.length) {
            projectsList.innerHTML = '<div class="text-xs text-muted p-2">No Vercel projects found</div>';
          } else {
            data.projects.forEach(proj => {
              const state = (proj.latest_deployment?.readyState || 'READY').toLowerCase();
              this.addSidebarItem(projectsList, proj.name, state, proj.name, {
                name: proj.name, env: 'Vercel Cloud', branch: 'production', type: 'vercel',
              });
            });
          }
        }
      } catch (err) {
        if (projectsList) projectsList.innerHTML = `<div class="text-xs text-danger p-2">${err.message}</div>`;
      }
    } else {
      if (dot) dot.className = 'status-dot';
      connectBox?.classList.remove('hidden');
      connectedBox?.classList.add('hidden');
    }
  }

  async refreshLocalState() {
    const dot = document.getElementById('local-status-dot');
    const list = document.getElementById('local-projects-list');
    try {
      const data = await this.api.getLocalProjects();
      if (dot) dot.className = 'status-dot success';
      if (list && data.projects?.length) {
        list.innerHTML = '';
        data.projects.forEach(p => this.addSidebarItem(list, `📁 ${p.name}`, p.current_branch, p.local_path, {
          name: p.name, env: 'Local Workspace', branch: p.current_branch, type: 'local',
        }));
      }
    } catch { if (dot) dot.className = 'status-dot'; }
  }

  addSidebarItem(list, label, badge, title, project) {
    const el = document.createElement('div');
    el.className = 'sidebar-item';
    el.setAttribute('role', 'button');
    el.setAttribute('tabindex', '0');
    el.innerHTML = `<span class="item-name" title="${title}">${label}</span><span class="badge badge-sm badge-info">${badge}</span>`;
    const choose = () => {
      this.setActiveProject(project);
      list.closest('.sidebar-integrations')?.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
      el.classList.add('active');
    };
    el.addEventListener('click', choose);
    el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(); } });
    list.appendChild(el);
  }

  // ── Active project = single source of truth ────────────────────
  setActiveProject(project) {
    this.activeProject = project;
    const ctxProject = document.getElementById('ctx-project');
    const ctxBranch = document.getElementById('ctx-branch');
    const objCtx = document.getElementById('objective-project-ctx');
    if (ctxProject) ctxProject.textContent = project.name;
    if (ctxBranch) ctxBranch.textContent = project.branch || 'main';
    if (objCtx) objCtx.innerHTML =
      `<span class="badge badge-sm badge-info">${project.type}</span> <strong>${project.name}</strong> · <span class="text-muted">${project.branch || 'main'}</span>`;
  }

  // ── Tabs ───────────────────────────────────────────────────────
  initTabRouting() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => this.activateTab(btn.getAttribute('data-tab')));
    });
  }
  activateTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(b => {
      const on = b.getAttribute('data-tab') === tabId;
      b.classList.toggle('active', on);
      b.setAttribute('aria-selected', String(on));
    });
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.id === tabId));
  }

  // ── Backend health ─────────────────────────────────────────────
  async checkBackendHealth() {
    const health = await this.api.checkHealth();
    const statusText = document.getElementById('system-status-text');
    const statusDot = document.getElementById('system-status-dot');
    if (health.status === 'ok') {
      if (statusText) statusText.textContent = 'BACKEND ONLINE';
      if (statusDot) statusDot.className = 'status-dot success';
      this.backendOnline = true;
    } else {
      if (statusText) statusText.textContent = 'BACKEND OFFLINE — DEMO ONLY';
      if (statusDot) statusDot.className = 'status-dot warning';
      this.backendOnline = false;
    }
  }

  // ── Objective execution ────────────────────────────────────────
  setObjectiveText(text) {
    const input = document.getElementById('objective-text-input');
    if (input) { input.value = text; input.focus(); }
  }

  handleStartObjective() {
    if (this.isRunning) return;
    const input = document.getElementById('objective-text-input');
    const objective = (input?.value || '').trim();
    if (!objective) { input?.focus(); return; }
    this.currentObjective = objective;

    this.isRunning = true;
    this.setRunningUI(true);
    this.stageRibbon.reset();
    this.liveTimeline.clear();
    this.toolPanel.reset();
    this.planPanel.setPlan(null);
    this.recoveryPanel.reset?.();
    this.deployPanel.reset();
    this.resultPanel.reset();
    this.updateAgentStatusBadge('EXECUTING', 'badge-active');
    this.activateTab('tab-plan');

    if (this.mode === 'demo') this.runMockExecution(objective);
    else this.runLiveAPIExecution(objective);
  }

  handleStopRun() {
    if (!this.isRunning) return;
    if (this.mode === 'demo') this.mock.stop();
    if (this.unsubscribe) { try { this.unsubscribe(); } catch {} this.unsubscribe = null; }
    this.isRunning = false;
    this.setRunningUI(false);
    this.updateAgentStatusBadge('STOPPED', 'badge-warning');
    this.liveTimeline.addEvent({ type: 'LOG', message: 'Run stopped by operator.', timestamp: new Date().toISOString() });
  }

  setRunningUI(running) {
    const start = document.getElementById('start-kalki-btn');
    const stop = document.getElementById('stop-kalki-btn');
    if (start) start.classList.toggle('hidden', running);
    if (stop) stop.classList.toggle('hidden', !running);
  }

  runMockExecution(objective) {
    this.activeRunId = this.mock.startMockExecution(
      objective,
      (evt) => this.handleIncomingEvent(evt),
      () => this.finishRun('demo'),
    );
  }

  async runLiveAPIExecution(objective) {
    try {
      const task = await this.api.createTask(objective, { project: this.activeProject?.name || 'Kalki', start: true });
      this.activeRunId = task.id;
      this.unsubscribe = this.api.subscribeToEvents(
        task.id,
        (evt) => this.handleIncomingEvent(evt),
        (err) => {
          console.error('SSE error:', err);
          this.liveTimeline.addEvent({ type: 'TOOL_FAILED', message: 'Event stream interrupted. The run may still be executing on the backend.', timestamp: new Date().toISOString() });
        },
        () => this.finishRun('live'),
      );
    } catch (err) {
      console.error('Live run failed to start:', err);
      this.liveTimeline.addEvent({ type: 'OBJECTIVE_FAILED', message: `Could not start live run: ${err.message}. Switch to DEMO mode to preview the flow.`, timestamp: new Date().toISOString() });
      this.updateAgentStatusBadge('FAILED', 'badge-error');
      this.isRunning = false;
      this.setRunningUI(false);
    }
  }

  async finishRun(kind) {
    this.isRunning = false;
    this.setRunningUI(false);
    if (kind === 'live' && this.activeRunId) {
      const result = await this.api.getResult(this.activeRunId).catch(() => null);
      if (result) this.presentResult(result);
    }
  }

  handleIncomingEvent(evt) {
    this.liveTimeline.addEvent(evt);
    if (evt.node) this.stageRibbon.setStage(evt.node, 'active');

    switch (evt.type) {
      case 'PLAN_CREATED':
      case 'PLAN_REVISED':
        if (evt.data?.plan) this.planPanel.setPlan(evt.data.plan);
        if (evt.type === 'PLAN_CREATED') this.stageRibbon.setStage('PLAN', 'completed');
        break;
      case 'TASK_STARTED':
        if (evt.data?.task_id) this.planPanel.updateTaskStatus(evt.data.task_id, 'running');
        break;
      case 'TOOL_STARTED':
        if (evt.data?.tool) this.toolPanel.setToolActive(evt.data.tool, true);
        break;
      case 'TOOL_COMPLETED':
        if (evt.data?.tool) this.toolPanel.addToolCall({ tool: evt.data.tool, duration_ms: evt.data.duration_ms, summary: evt.message });
        break;
      case 'TOOL_FAILED':
        if (evt.data?.tool) this.toolPanel.setToolActive(evt.data.tool, false);
        break;
      case 'MEMORY_RETRIEVED':
        if (evt.data?.memory) this.memoryPanel.setMemory(evt.data.memory);
        break;
      case 'MEMORY_STORED':
        this.stageRibbon.setStage('LEARN', 'active');
        break;
      case 'RECOVERY_STARTED':
        if (evt.data) { this.recoveryPanel.setRecovery(evt.data); this.stageRibbon.setStage('RECOVERING', 'active'); this.flashTab('tab-recovery'); }
        this.updateAgentStatusBadge('RECOVERING', 'badge-warning');
        break;
      case 'CODE_CHANGED':
        if (evt.data) { this.codeDiffView.setDiff(evt.data); this.flashTab('tab-code'); }
        break;
      case 'TEST_STARTED':
      case 'TEST_FAILED':
      case 'TEST_PASSED':
        if (evt.data) this.testPanel.setTestState({ ...evt.data, phase: evt.type });
        if (evt.type === 'TEST_FAILED') this.updateAgentStatusBadge('DIAGNOSING', 'badge-warning');
        if (evt.type === 'TEST_PASSED') this.updateAgentStatusBadge('EXECUTING', 'badge-active');
        break;
      case 'DEPLOY_STARTED':
      case 'DEPLOY_COMPLETED':
        if (evt.data) this.deployPanel.setDeployState({ ...evt.data, phase: evt.type });
        break;
      case 'VERIFICATION_STARTED':
        this.stageRibbon.setStage('VERIFY', 'active');
        break;
      case 'VERIFICATION_COMPLETED':
        this.stageRibbon.setStage('VERIFY', 'completed');
        break;
      case 'APPROVAL_REQUIRED':
        if (evt.data?.tool) {
          this.deployPanel.setApprovalRequired(true, [evt.data.tool]);
          this.updateAgentStatusBadge('AWAITING APPROVAL', 'badge-warning');
          this.activateTab('tab-deploy');
        }
        break;
      case 'OBJECTIVE_COMPLETED':
      case 'TASK_COMPLETED':
        this.stageRibbon.setStage('LEARN', 'completed');
        this.updateAgentStatusBadge('COMPLETED', 'badge-success');
        this.presentResult({ status: 'completed', objective: evt.data?.objective, ...evt.data });
        break;
      case 'OBJECTIVE_FAILED':
      case 'TASK_FAILED':
        this.updateAgentStatusBadge('FAILED', 'badge-error');
        this.presentResult({ status: 'failed', ...evt.data });
        break;
    }
  }

  presentResult(result) {
    if (!result.objective && this.currentObjective) result.objective = this.currentObjective;
    this.resultPanel.setResult(result, {
      project: this.activeProject,
      events: this.liveTimeline.events,
    });
    this.activateTab('tab-result');
  }

  flashTab(tabId) {
    const btn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
    if (btn) { btn.classList.add('flash'); setTimeout(() => btn.classList.remove('flash'), 1200); }
  }

  async handleApproveGatedAction(tools) {
    if (this.activeRunId && this.mode === 'live') {
      await this.api.approveTask(this.activeRunId, tools).catch(e => console.error('approve failed', e));
    }
    this.deployPanel.setApprovalRequired(false);
    this.updateAgentStatusBadge('EXECUTING', 'badge-active');
  }

  updateAgentStatusBadge(text, badgeClass) {
    const badge = document.getElementById('ctx-agent-status');
    if (badge) { badge.className = `badge ${badgeClass}`; badge.textContent = text; }
  }
}

document.addEventListener('DOMContentLoaded', () => { window.kalkiApp = new KalkiApp(); });
