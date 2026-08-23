/**
 * KALKI — Code Diff Viewer
 * Renders the actual diff carried on a CODE_CHANGED event. Parses unified-diff
 * text into +/- lines; falls back to a summary when no diff body is provided.
 */

export class CodeDiffView {
  constructor(container) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.diffData = null;
    this.render();
  }

  setDiff(data) { this.diffData = data; this.render(); }
  reset() { this.diffData = null; this.render(); }

  _escape(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  _renderDiffBody(diff) {
    const lines = diff.split('\n');
    let added = 0, removed = 0;
    const rows = lines.map(line => {
      let cls = '';
      if (line.startsWith('+') && !line.startsWith('+++')) { cls = 'add'; added++; }
      else if (line.startsWith('-') && !line.startsWith('---')) { cls = 'del'; removed++; }
      else if (line.startsWith('@@')) cls = 'hunk';
      return `<div class="diff-line ${cls}"><span>${this._escape(line) || '&nbsp;'}</span></div>`;
    }).join('');
    return { rows, added, removed };
  }

  render() {
    const d = this.diffData;
    if (!d) {
      this.container.innerHTML = `
        <div class="panel-empty">
          <div class="panel-empty-icon">📝</div>
          <div class="font-mono panel-empty-title">CODE CHANGES</div>
          <div class="panel-empty-sub">File edits and diffs render here when KALKI modifies code.</div>
        </div>`;
      return;
    }

    let body = '', added = d.added, removed = d.removed;
    if (d.diff) {
      const parsed = this._renderDiffBody(d.diff);
      body = parsed.rows;
      if (added == null) added = parsed.added;
      if (removed == null) removed = parsed.removed;
    }

    this.container.innerHTML = `
      <div class="diff-container">
        <div class="diff-header">
          <div class="flex-center gap-2" style="min-width:0;">
            <span>📝</span>
            <span class="diff-file" style="font-weight:700;color:var(--accent-cyan);">${this._escape(d.file || 'modified file')}</span>
            ${added != null ? `<span class="badge badge-success">+${added}</span>` : ''}
            ${removed != null ? `<span class="badge badge-failure">-${removed}</span>` : ''}
          </div>
          ${d.summary ? `<span class="diff-summary text-muted">${this._escape(d.summary)}</span>` : ''}
        </div>
        <div class="diff-body">
          ${body || `<div class="diff-line"><span>${this._escape(d.summary || 'Change recorded (no diff body provided).')}</span></div>`}
        </div>
      </div>`;
  }
}
