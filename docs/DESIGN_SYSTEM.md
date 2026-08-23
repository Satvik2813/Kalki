# KALKI — Design System & Brand

**KALKI — Autonomous AI Software Engineer.**

This document is the reference for the KALKI front-end visual language. It was
introduced in the front-end overhaul that turned the functional prototype into a
premium autonomous-engineering workspace.

---

## 1. Brand

- **Name:** KALKI
- **Descriptor:** Autonomous AI Software Engineer
- **Positioning:** *Your autonomous software engineer.* Give KALKI a repository and
  an engineering objective; it plans, inspects, writes code, runs tests, recovers
  from failures, and verifies the result — end to end.
- **Personality:** intelligent, autonomous, precise, trustworthy, engineering-grade,
  futuristic but professional. Not a chat toy, not a generic dashboard.

### Logo / mark
The mark is a geometric **K** monogram inside a rounded engineering badge, with an
**autonomous decision node** (the dot at the K's junction, ringed) signalling agency.

| Asset | File | Use |
|-------|------|-----|
| Icon / favicon | `frontend/assets/kalki-mark.svg` | Browser tab, square avatar, small sizes |
| Horizontal lockup | `frontend/assets/kalki-logo.svg` | Marketing / external use |
| In-app wordmark | `frontend/js/branding/wordmark.js` (`renderKalkiWordmark`) | Navbar, landing, auth, sidebar |

All assets are **self-contained SVG in the repository** and use the brand gradient.

> **Canva MCP note:** the Canva connector requires interactive OAuth and was not
> authorizable in the non-interactive build session, so — per the brief's fallback
> clause — the mark was authored directly as production SVG in the repo rather than
> exported from Canva. The SVG is implementation-ready and needs no external asset.

---

## 2. Color

Dark-first "engineering console". One signature accent; glow is reserved strictly
for **active / live** state, never decoration. Tokens live in
`frontend/css/kalki-theme.css`.

| Role | Token | Value |
|------|-------|-------|
| Page ground | `--bg-void` | `#060708` |
| Panel | `--bg-panel` / `--bg-surface` | `#121419` / `#16181e` |
| Signature accent | `--accent-cyan` | `#22d3ee` |
| Accent (secondary) | `--accent-blue` / `--accent-purple` | `#38bdf8` / `#a78bfa` |
| Success | `--color-success` | `#34d399` |
| Warning | `--color-warning` | `#fbbf24` |
| Failure | `--color-failure` | `#f87171` |
| Text | `--text-bright` / `--text-primary` / `--text-secondary` / `--text-muted` | `#f6f8fb` → `#6c7382` |
| Borders | `--border-subtle` / `--border-main` | `rgba(255,255,255,.06/.12)` |

> **Why the redesign started here:** the old `components.css` referenced ~25 CSS
> variables (`--bg-surface`, `--text-primary`, `--color-success`, …) that *no
> stylesheet defined*, so most panels rendered transparent/borderless. The theme is
> now the single authoritative token set both stylesheets consume.

## 3. Typography

- **Display:** Outfit (headings, wordmark, hero)
- **UI / body:** Inter
- **Data / code / status:** JetBrains Mono

## 4. Scale

- **Radius:** `--radius-xs 4` · `sm 6` · `md 10` · `lg 14`
- **Spacing:** 4 / 8 / 12 / 16 / 24 / 32 / 48
- **Elevation:** `--shadow-panel` (panels), `--shadow-elev` (modals), `--border-glow` (active)
- **Motion:** 0.18s standard; `--ease-out` for entrances. Honors
  `prefers-reduced-motion` (animations disabled).

## 5. Components

Buttons (`.btn`, `.btn-accent`, `.btn-primary`, `.btn-outline`, `.btn-link`, sizes),
badges (`.badge-*` incl. success/warning/failure/purple), status dots
(`.status-dot.success|active|warning|error`), inputs, glass panels, tabs, cards,
and shared **empty states** (`.panel-empty`). New screen styles are in
`frontend/css/kalki-screens.css`.

## 6. Accessibility

- Visible focus rings (`:focus-visible`) on all controls.
- Semantic buttons; `role`/`aria-*` on tabs, accordions, dialog, source cards.
- Keyboard activation for accordions and sidebar items (Enter/Space).
- `prefers-reduced-motion` respected. `.sr-only` helper for labels.

## 7. Responsive breakpoints

`1024px` (timeline stacks over tabs, source grid → 1 col), `768px` (sidebar becomes
a top strip, context bar wraps), `480px` (header wraps, subtitle hidden). Verified:
no horizontal overflow at 375 / 768 / 1024 / 1280.
