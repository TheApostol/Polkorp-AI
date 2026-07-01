# CLAUDE.md

Guidance for working on this repository.

## What this repo is

`TheApostol/Polkorp-AI` is a single-file cinematic command dashboard for
POLKORP AI — a private launcher UI for locally-hosted AI tools (Ollama,
Fooocus, Lama Cleaner, Upscayl, DeepSeek Coder, etc). It is a front-end
only: a login gate, a natural-language router, and a card grid that
launches tools. It does not itself run models or host a backend.

**Do not confuse this with `TheApostol/polkorp`.** That is a separate,
unrelated product — a real CRM/SaaS suite (`polkorp.com` marketing site +
Next.js dashboard + FastAPI backend + Supabase auth with tenant
isolation). The two repos share a name prefix and nothing else.

## Deliverable

- `polkorpai.html` — the entire dashboard. Single file, inline CSS, inline
  JS, zero external dependencies, must work fully offline (opened via
  `file://` with no server).
- `index.html` at the repo root predates this work and is unrelated —
  leave it alone unless asked to touch it.
- `assets/logos/` holds the source POLKORP AI logo/emblem SVGs and PNGs.
  The emblem SVG is inlined directly into `polkorpai.html` (once for the
  login screen, once — with renamed filter IDs to avoid SVG `id`
  collisions — for the dashboard header) rather than referenced as an
  external file, to keep the single-file requirement intact.

## Design tokens

Extracted from the logo, not invented:

```
--primary:   #00d4ff  (cyan)
--secondary: #0066ff  (blue)
--success:   #00ff88
--warning:   #ffaa00
--error:     #ff3333
--bg:        #0a0a0f
font stack:  'SF Mono', 'Fira Code', 'Courier New', monospace
```

Motion direction is intentionally restrained: cinematic, Apple /
Blade Runner / Interstellar-adjacent. Avoid neon overload, hacker
clichés, or gaming-UI excess — glows and gradients should be subtle.

## Auth mechanism

The access code is checked client-side via
`crypto.subtle.digest("SHA-256", ...)` against a hardcoded hex hash
constant (`ACCESS_HASH`) in the script. The plaintext code is never
stored in the file or in this doc — if you need it, it's in the task
history that produced this repo, not in source.

Session state: `sessionStorage.polkorp_authenticated`. On load, if that
flag is `"true"`, the login screen is skipped and the dashboard boots
directly.

**Ordering constraint that matters:** the bootstrap check
(`sessionStorage.getItem(...) → enterDashboard() / runLoginSequence()`)
must run *after* every function and data structure it depends on
(`CARDS`, `ROUTES`, `renderCards`, etc.) is defined earlier in the same
script. It was previously placed mid-script and broke the
already-authenticated/refresh path — see `PROJECT_MEMORY.md`.

## Where things live in the script

- `ROUTES` — the keyword → {tool, category} table the command prompt
  uses to route free-text input. Edited in place; checked top-to-bottom,
  first match wins.
- `CARDS` — the data for the 6-card grid (icon, title, subtitle, submenu
  items, `wide`/`dimmed`/`badge` flags). `renderCards()` builds the DOM
  from this array.
- Local folder connector — `connectLocalFolder()` uses
  `window.showDirectoryPicker()` (File System Access API). Chromium-only
  by design (graceful toast fallback elsewhere); nothing is uploaded, the
  handle stays in memory for the tab.

## Testing convention

There's no test suite — verification is done with a headless browser:

```bash
NODE_PATH=/opt/node22/lib/node_modules node your-script.js
```

using Playwright's pre-installed Chromium at `/opt/pw-browsers/chromium`
(Playwright itself is only available globally under `/opt/node22`, not
in a local `node_modules`). Screenshot the login sequence, the password
success/failure states, and the dashboard after authenticating — that's
what caught the bootstrap-ordering bug.

## Branch

Active work happens on `claude/polkorp-ai-dashboard-s64uhn`.
