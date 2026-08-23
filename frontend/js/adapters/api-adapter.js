/**
 * KALKI — FastAPI Backend & Integration Adapter
 * Connects the UI directly to KALKI identity, integrations, and agent runs.
 */

export class KalkiAPIAdapter {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
    this.tokenKey = 'kalki_auth_token';
  }

  getToken() {
    return localStorage.getItem(this.tokenKey) || '';
  }

  setToken(token) {
    if (token) {
      localStorage.setItem(this.tokenKey, token);
    }
  }

  clearToken() {
    localStorage.removeItem(this.tokenKey);
  }

  _headers(extra = {}) {
    const headers = { 'Content-Type': 'application/json', ...extra };
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  /**
   * Health check endpoint
   */
  async checkHealth() {
    try {
      const res = await fetch(`${this.baseUrl}/health`);
      return await res.json();
    } catch (err) {
      console.warn('API Health check failed:', err);
      return { status: 'offline', error: err.message };
    }
  }

  // ── Auth Endpoints ──────────────────────────────────────────

  async getMe() {
    try {
      const res = await fetch(`${this.baseUrl}/api/auth/me`, {
        headers: this._headers(),
      });
      if (!res.ok) return { authenticated: false };
      return await res.json();
    } catch (err) {
      return { authenticated: false };
    }
  }

  async loginGuest() {
    const res = await fetch(`${this.baseUrl}/api/auth/guest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error('Guest login failed');
    const data = await res.json();
    if (data.token) {
      this.setToken(data.token);
    }
    return data;
  }

  // ── Integrations: GitHub ────────────────────────────────────

  async getGitHubStatus() {
    try {
      const res = await fetch(`${this.baseUrl}/api/integrations/github/status`, {
        headers: this._headers(),
      });
      if (!res.ok) return { connected: false };
      return await res.json();
    } catch {
      return { connected: false };
    }
  }

  async getGitHubRepos() {
    const res = await fetch(`${this.baseUrl}/api/integrations/github/repos`, {
      headers: this._headers(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch GitHub repositories');
    }
    return await res.json();
  }

  async disconnectGitHub() {
    const res = await fetch(`${this.baseUrl}/api/integrations/github/disconnect`, {
      method: 'POST',
      headers: this._headers(),
    });
    return await res.json();
  }

  // ── Integrations: Vercel ────────────────────────────────────

  async getVercelStatus() {
    try {
      const res = await fetch(`${this.baseUrl}/api/integrations/vercel/status`, {
        headers: this._headers(),
      });
      if (!res.ok) return { connected: false };
      return await res.json();
    } catch {
      return { connected: false };
    }
  }

  async connectVercel(token) {
    const res = await fetch(`${this.baseUrl}/api/integrations/vercel/connect`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify({ token }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to connect Vercel token');
    }
    return await res.json();
  }

  async getVercelProjects() {
    const res = await fetch(`${this.baseUrl}/api/integrations/vercel/projects`, {
      headers: this._headers(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch Vercel projects');
    }
    return await res.json();
  }

  async disconnectVercel() {
    const res = await fetch(`${this.baseUrl}/api/integrations/vercel/disconnect`, {
      method: 'POST',
      headers: this._headers(),
    });
    return await res.json();
  }

  // ── Integrations: Local Repository ──────────────────────────

  async connectLocal(data = {}) {
    const res = await fetch(`${this.baseUrl}/api/integrations/local/connect`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to register local project');
    return await res.json();
  }

  async getLocalProjects() {
    try {
      const res = await fetch(`${this.baseUrl}/api/integrations/local/projects`, {
        headers: this._headers(),
      });
      if (!res.ok) return { projects: [] };
      return await res.json();
    } catch {
      return { projects: [] };
    }
  }

  // ── Core Task & Agent Endpoints ─────────────────────────────

  async createTask(objective, options = {}) {
    const res = await fetch(`${this.baseUrl}/api/tasks`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify({
        objective,
        project: options.project || 'Kalki',
        autonomy: options.autonomy || 'autonomous',
        start: options.start ?? true,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to create task`);
    return await res.json();
  }

  async startTask(runId) {
    const res = await fetch(`${this.baseUrl}/api/tasks/${runId}/start`, {
      method: 'POST',
      headers: this._headers(),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to start task`);
    return await res.json();
  }

  async getResult(runId) {
    const res = await fetch(`${this.baseUrl}/api/tasks/${runId}/result`, {
      headers: this._headers(),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch result`);
    return await res.json();
  }

  async approveTask(runId, tools = []) {
    const res = await fetch(`${this.baseUrl}/api/tasks/${runId}/approve`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify({ tools }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to approve task`);
    return await res.json();
  }

  subscribeToEvents(runId, onEvent, onError, onComplete) {
    const sseUrl = `${this.baseUrl}/api/tasks/${runId}/events?stream=1`;
    const eventSource = new EventSource(sseUrl);

    eventSource.onmessage = (e) => {
      try {
        const eventData = JSON.parse(e.data);
        onEvent(eventData);
      } catch (err) {
        console.error('Failed to parse SSE event:', err);
      }
    };

    const eventTypes = [
      'PLAN_CREATED', 'PLAN_REVISED', 'TASK_STARTED', 'TOOL_STARTED',
      'TOOL_COMPLETED', 'TOOL_FAILED', 'MEMORY_RETRIEVED', 'MEMORY_STORED',
      'CODE_CHANGED', 'TEST_STARTED', 'TEST_FAILED', 'TEST_PASSED',
      'RECOVERY_STARTED', 'DEPLOY_STARTED', 'DEPLOY_COMPLETED',
      'VERIFICATION_STARTED', 'VERIFICATION_COMPLETED', 'APPROVAL_REQUIRED',
      'TASK_COMPLETED', 'TASK_FAILED', 'OBJECTIVE_COMPLETED', 'OBJECTIVE_FAILED', 'LOG'
    ];

    eventTypes.forEach((evtType) => {
      eventSource.addEventListener(evtType, (e) => {
        try {
          const eventData = JSON.parse(e.data);
          onEvent(eventData);
        } catch (err) {
          console.error(`Error parsing SSE ${evtType}:`, err);
        }
      });
    });

    eventSource.addEventListener('_end', (e) => {
      eventSource.close();
      if (onComplete) onComplete(JSON.parse(e.data || '{}'));
    });

    eventSource.onerror = (err) => {
      console.warn('SSE EventSource error:', err);
      if (onError) onError(err);
    };

    return () => {
      eventSource.close();
    };
  }

  async getProjects() {
    try {
      const res = await fetch(`${this.baseUrl}/api/projects`, {
        headers: this._headers(),
      });
      return await res.json();
    } catch {
      return { projects: ['Kalki', 'Satvik2813/Kalki'] };
    }
  }

  async getMemories(limit = 50) {
    try {
      const res = await fetch(`${this.baseUrl}/api/memory?limit=${limit}`, {
        headers: this._headers(),
      });
      return await res.json();
    } catch {
      return { memories: [] };
    }
  }
}
