/**
 * KALKI — Professional Code Diff Viewer Component
 */

export class CodeDiffView {
  constructor(container) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.diffData = null;
    this.render();
  }

  setDiff(data) {
    this.diffData = data;
    this.render();
  }

  render() {
    if (!this.diffData) {
      this.container.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 40px 0;">
          <div style="font-size: 28px; margin-bottom: 8px;">📝</div>
          <div class="font-mono" style="font-weight: 600;">CODE CHANGES & DIFF VIEWER</div>
          <div style="font-size: 11px; margin-top: 4px;">Modified files and syntax-highlighted diffs will render here when KALKI edits code</div>
        </div>
      `;
      return;
    }

    const d = this.diffData;

    const html = `
      <div class="diff-container">
        <div class="diff-header">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span>📝</span>
            <span style="font-weight: 700; color: var(--accent-cyan);">${d.file || 'src/auth/middleware.py'}</span>
            <span class="badge badge-success">+14</span>
            <span class="badge badge-failure">-4</span>
          </div>
          <span style="color: var(--text-muted); font-size: 11px;">${d.summary || 'Added 60s clock skew tolerance to PyJWT verify context'}</span>
        </div>

        <div class="diff-body">
          <div class="diff-line"><span class="diff-num">40</span><span>def verify_jwt_token(token: str):</span></div>
          <div class="diff-line"><span class="diff-num">41</span><span>    """Verifies incoming JWT session token with clock skew safety."""</span></div>
          <div class="diff-line del"><span class="diff-num">42</span><span>-   payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])</span></div>
          <div class="diff-line add"><span class="diff-num">42</span><span>+   payload = jwt.decode(</span></div>
          <div class="diff-line add"><span class="diff-num">43</span><span>+       token,</span></div>
          <div class="diff-line add"><span class="diff-num">44</span><span>+       SECRET_KEY,</span></div>
          <div class="diff-line add"><span class="diff-num">45</span><span>+       algorithms=["HS256"],</span></div>
          <div class="diff-line add"><span class="diff-num">46</span><span>+       leeway=60  # Added 60s clock-skew tolerance per INC-037</span></div>
          <div class="diff-line add"><span class="diff-num">47</span><span>+   )</span></div>
          <div class="diff-line"><span class="diff-num">48</span><span>    return payload</span></div>
        </div>
      </div>
    `;

    this.container.innerHTML = html;
  }
}
