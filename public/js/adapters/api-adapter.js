/**
 * KALKI — FastAPI Backend Adapter
 * Connects the UI directly to Dev 1's FastAPI endpoints & SSE streams
 */

export class KalkiAPIAdapter {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
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

  /**
   * Create a new task / run objective
   */
  async createTask(objective, options = {}) {
    const res = await fetch(`${this.baseUrl}/api/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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

  /**
   * Start execution for created task
   */
  async startTask(runId) {
    const res = await fetch(`${this.baseUrl}/api/tasks/${runId}/start`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to start task`);
    return await res.json();
  }

  /**
   * Approve gated tool execution
   */
  async approveTask(runId, tools = []) {
    const res = await fetch(`${this.baseUrl}/api/tasks/${runId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tools }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to approve task`);
    return await res.json();
  }

  /**
   * Subscribe to Server-Sent Events (SSE) stream for a task
   */
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

    // Specific event listeners for EventType values
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

  /**
   * Fetch known projects
   */
  async getProjects() {
    try {
      const res = await fetch(`${this.baseUrl}/api/projects`);
      return await res.json();
    } catch {
      return { projects: ['Kalki', 'Satvik2813/Kalki'] };
    }
  }

  /**
   * Fetch recent memories
   */
  async getMemories(limit = 50) {
    try {
      const res = await fetch(`${this.baseUrl}/api/memory?limit=${limit}`);
      return await res.json();
    } catch {
      return { memories: [] };
    }
  }
}
