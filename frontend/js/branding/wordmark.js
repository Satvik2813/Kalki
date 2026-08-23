/**
 * KALKI — Brand Wordmark
 *
 * Inline SVG lockup: geometric "K" mark (with autonomous decision node) plus
 * the KALKI wordmark. Rendered from the same design tokens as the app so the
 * navbar logo, favicon (assets/kalki-mark.svg), and lockup stay consistent.
 */

export function renderKalkiWordmark(container, options = {}) {
  const height = options.height || 28;
  const showText = options.showText !== false;

  const svgHTML = `
    <svg class="kalki-logo-svg" height="${height}" viewBox="0 0 ${showText ? 176 : 44} 44"
         fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="KALKI">
      <defs>
        <linearGradient id="kalkiWmGrad" x1="4" y1="6" x2="36" y2="38" gradientUnits="userSpaceOnUse">
          <stop offset="0" stop-color="#22d3ee"/>
          <stop offset="1" stop-color="#3b82f6"/>
        </linearGradient>
      </defs>
      <rect x="2.5" y="2.5" width="39" height="39" rx="9.5" fill="#0d0f13"
            stroke="url(#kalkiWmGrad)" stroke-width="1.4"/>
      <g stroke="url(#kalkiWmGrad)" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" fill="none">
        <line x1="14" y1="11" x2="14" y2="33"/>
        <line x1="29.5" y1="11" x2="16.2" y2="22"/>
        <line x1="16.2" y1="22" x2="29.5" y2="33"/>
      </g>
      <circle cx="16.2" cy="22" r="2.3" fill="#22d3ee"/>
      ${showText ? `
      <text x="56" y="29" font-family="Outfit, 'Segoe UI', sans-serif" font-size="22"
            font-weight="800" letter-spacing="4" fill="#f6f8fb">KALKI</text>
      ` : ''}
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
