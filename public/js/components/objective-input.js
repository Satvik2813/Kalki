/**
 * KALKI — Onboarding / Objective Input Component
 */

export function renderObjectiveInput(container, options = {}) {
  const html = `
    <div class="onboarding-container" id="onboarding-step-login">
      <h1 class="onboarding-title">Initialize KALKI</h1>
      <p class="onboarding-subtitle">Autonomous AI Software Engineer</p>
      
      <button id="btn-login" class="btn-kalki-primary" style="margin: 0 auto;">
        <span>CONNECT WORKSPACE</span>
        <span>→</span>
      </button>
    </div>

    <div class="onboarding-container" id="onboarding-step-project" style="display: none;">
      <h1 class="onboarding-title">Select Project Context</h1>
      <p class="onboarding-subtitle">Where should KALKI operate?</p>
      
      <div class="project-grid">
        <div class="project-card" data-project="github:owner/repo">
          <div class="project-title">GitHub Repository</div>
          <div class="project-desc">Pull, branch, commit, and open PRs.</div>
        </div>
        <div class="project-card" data-project="vercel:prj_id">
          <div class="project-title">Vercel Project</div>
          <div class="project-desc">Deploy and verify previews.</div>
        </div>
        <div class="project-card" data-project="local:workspace">
          <div class="project-title">Local Repository</div>
          <div class="project-desc">Run isolated in the local sandbox.</div>
        </div>
        <div class="project-card disabled" data-project="zip">
          <div class="project-title">ZIP Upload</div>
          <div class="project-desc">Coming Soon</div>
        </div>
      </div>
      
      <button id="btn-next-objective" class="btn-kalki-primary" style="margin: 0 auto; display: none;">
        <span>CONTINUE</span>
        <span>→</span>
      </button>
    </div>

    <div class="onboarding-container" id="onboarding-step-objective" style="display: none;">
      <h1 class="onboarding-title">Engineering Objective</h1>
      <p class="onboarding-subtitle">What should KALKI accomplish?</p>
      
      <div class="objective-box" style="margin-bottom: 24px; flex-direction: column;">
        <textarea 
          id="objective-text-input" 
          class="objective-input" 
          style="min-height: 80px; resize: none; font-size: 14px;"
          placeholder="e.g. Find the authentication bug, fix it, run the tests, deploy the fix, and verify the deployment."
        >Fix authentication token expiration bug, run tests, deploy fix and verify production.</textarea>
      </div>

      <div class="objective-actions" style="justify-content: center;">
        <button id="start-kalki-btn" class="btn-kalki-primary">
          <span>START KALKI</span>
          <span>→</span>
        </button>
      </div>
    </div>
  `;

  if (typeof container === 'string') {
    document.querySelector(container).innerHTML = html;
  } else {
    container.innerHTML = html;
  }

  // DOM Elements
  const stepLogin = document.getElementById('onboarding-step-login');
  const stepProject = document.getElementById('onboarding-step-project');
  const stepObjective = document.getElementById('onboarding-step-objective');
  
  const btnLogin = document.getElementById('btn-login');
  const btnNextObj = document.getElementById('btn-next-objective');
  const btnStart = document.getElementById('start-kalki-btn');
  const inputEl = document.getElementById('objective-text-input');
  const projectCards = document.querySelectorAll('.project-card:not(.disabled)');

  let selectedProject = null;

  // Step 1: Login
  btnLogin.addEventListener('click', () => {
    stepLogin.style.display = 'none';
    stepProject.style.display = 'block';
  });

  // Step 2: Project Selection
  projectCards.forEach(card => {
    card.addEventListener('click', () => {
      projectCards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      selectedProject = card.getAttribute('data-project');
      btnNextObj.style.display = 'flex';
    });
  });

  btnNextObj.addEventListener('click', () => {
    stepProject.style.display = 'none';
    stepObjective.style.display = 'block';
    inputEl.focus();
  });

  // Step 3: Start Execution
  const triggerStart = () => {
    const val = inputEl.value.trim();
    if (!val) return;
    
    // Hide the overlay container
    const overlay = document.getElementById('onboarding-overlay');
    if (overlay) {
      overlay.classList.add('hidden');
    }

    if (options.onStart) {
      options.onStart(val, selectedProject);
    }
  };

  btnStart.addEventListener('click', triggerStart);
}
