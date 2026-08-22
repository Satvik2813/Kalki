/**
 * KALKI — Custom Geometric Typography & Wordmark Component
 * 
 * Generates vector geometric SVG lettering for the KALKI wordmark with:
 * - Geometric lettering constructed from straight lines & sharp angles
 * - Thin sharp strokes with A-like triangular geometry
 * - Wide letter tracking
 * - Futuristic engineering precision
 */

export function renderKalkiWordmark(container, options = {}) {
  const height = options.height || 28;
  
  const svgHTML = `
    <svg class="kalki-logo-svg" height="${height}" viewBox="0 0 340 50" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <!-- Glow Filter -->
        <filter id="cyanGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="1.5" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
        <linearGradient id="cyanGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#00f0ff" />
          <stop offset="100%" stop-color="#38bdf8" />
        </linearGradient>
      </defs>

      <!-- Letter K -->
      <g class="letter-k" stroke="url(#cyanGrad)" stroke-width="2.5" stroke-linecap="square" filter="url(#cyanGlow)">
        <line x1="10" y1="10" x2="10" y2="40" />
        <line x1="32" y1="10" x2="10" y2="25" />
        <line x1="10" y1="25" x2="32" y2="40" />
      </g>

      <!-- Letter A (Triangular Geometric Apex) -->
      <g class="letter-a" stroke="url(#cyanGrad)" stroke-width="2.5" stroke-linecap="square" filter="url(#cyanGlow)">
        <polyline points="50,40 68,10 86,40" />
        <line x1="58" y1="28" x2="78" y2="28" />
        <!-- Sharp Inner Triangular Notch -->
        <polygon points="68,16 64,24 72,24" fill="#00f0ff" opacity="0.6" />
      </g>

      <!-- Letter L -->
      <g class="letter-l" stroke="url(#cyanGrad)" stroke-width="2.5" stroke-linecap="square" filter="url(#cyanGlow)">
        <line x1="105" y1="10" x2="105" y2="40" />
        <line x1="105" y1="40" x2="127" y2="40" />
      </g>

      <!-- Letter K -->
      <g class="letter-k2" stroke="url(#cyanGrad)" stroke-width="2.5" stroke-linecap="square" filter="url(#cyanGlow)">
        <line x1="145" y1="10" x2="145" y2="40" />
        <line x1="167" y1="10" x2="145" y2="25" />
        <line x1="145" y1="25" x2="167" y2="40" />
      </g>

      <!-- Letter I -->
      <g class="letter-i" stroke="url(#cyanGrad)" stroke-width="2.5" stroke-linecap="square" filter="url(#cyanGlow)">
        <line x1="187" y1="10" x2="207" y2="10" />
        <line x1="197" y1="10" x2="197" y2="40" />
        <line x1="187" y1="40" x2="207" y2="40" />
      </g>

      <!-- Geometric Accent Dots & Subtitle Mark -->
      <circle cx="225" cy="25" r="2" fill="#00f0ff" filter="url(#cyanGlow)" />
      <text x="238" y="28" fill="#8b949e" font-family="'JetBrains Mono', monospace" font-size="11" font-weight="700" letter-spacing="3">AI CORE</text>
    </svg>
  `;

  if (typeof container === 'string') {
    const el = document.querySelector(container);
    if (el) el.innerHTML = svgHTML;
  } else if (container) {
    container.innerHTML = svgHTML;
  }
  return svgHTML;
}
