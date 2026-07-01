# PROJECT_MEMORY.md

Chronological log of decisions made while building `polkorpai.html`.
Newest at the bottom.

## 1. Initial spec (superseded)

First spec requested a hacker/OSINT-themed dashboard: heavy cyberpunk
grid-line background, embers, a card literally named "HACK / OSINT" with
items like Payload Builder (LLM), Wordlist Gen (AI), Hash Cracking, and
copy like "No restrictions. No logs. No filters." This was **not**
built — before implementation started, the user replaced it with a
cleaner revised spec (see #2).

## 2. Revised spec — the one actually built

User provided a full replacement spec: softer tone ("Uncapped.
Unlimited. A Simple Corp." / "Private. Secure. User-controlled."),
restrained motion direction (explicitly: avoid neon overload, hacker
clichés, gaming UI — aim for Apple / Blade Runner / Interstellar-style
polish), and a renamed Card 4: `SECURITY` with benign items (OSINT,
Recon, Security Analysis, Audits) instead of the earlier dual-use-tool
framing. This spec is what `polkorpai.html` implements.

Router keyword table, card grid (6 cards: Code, Image, Video, Security,
Orchestrate, Tools), history panel, terminal panel, toast system, and
status bar were all built per this spec.

## 3. File built and named

Built as a single self-contained HTML file per spec, verified with
Playwright (login sequence timing, password success/failure states,
router → card-highlight flow, history panel, terminal commands — no
console errors). User then asked to name the deliverable
`polkorpai.html` instead of the spec's default `index.html`. The repo's
pre-existing `index.html` (an unrelated prior build, ~200KB) was left
untouched.

## 4. Wordmark added

User asked for a "POLKORP AI" wordmark above the login logo, styled
distinctly ("fabulous letter"). Added as a gradient-text `<h1>`
(cyan → white → blue, matching the logo palette) that cascades in
slightly before the emblem's entrance rotation, rather than duplicating
the text already baked into the full logo SVG.

## 5. Living color + floating logo + local folder connector

Three requests bundled together:

- **Animated color motion**: the wordmark's gradient was static; user
  wanted it continuously shifting. Changed to a wide (300%) background
  gradient with an infinite `background-position` keyframe animation.
  Applied the same treatment to the dashboard header title for
  consistency.
- **Floating 3D logo**: the login logo only animated once (entrance
  rotation/scale). User wanted a continuous idle float. Rather than
  adding a second animation to the same element (which would fight the
  entrance `transition` — both target `transform`), split it into a
  nested `.login-logo-float` layer with its own infinite bob/tilt
  keyframe, independent of the outer entrance transform.
- **Local folder connector**: added a folder icon button in the header
  plus an inline "browse" link under the command prompt, using
  `window.showDirectoryPicker()` (File System Access API). Read-only,
  in-memory for the tab, no upload — chosen specifically because it
  needs no backend and so doesn't compromise the single-file/offline
  design. Real connectors to GitHub/Claude/Cortex-style services were
  explicitly discussed and deferred (see below) since those need a
  credential-holding backend.

## 6. Bug found and fixed: bootstrap ordering

While testing the "already authenticated, tab refreshed" path with
Playwright (`sessionStorage.polkorp_authenticated = "true"` then
reload), the page threw: `renderCards` called `CARDS.forEach` before
`CARDS` was assigned, because the bootstrap check
(`if (sessionStorage...) enterDashboard(); else runLoginSequence();`)
was placed mid-script, before the `CARDS`/`ROUTES` declarations further
down. This was a real bug in every version up to that point — the
normal login flow never hit it because `grantAccess()` calls
`enterDashboard()` from inside a `setTimeout`, which runs after the
whole script (including the later declarations) has already executed.
Fixed by moving the bootstrap check to the very end of the IIFE.

## Open / deferred

- **Real backend connectors** (GitHub, Claude, Cortex-style
  integrations): discussed when the user asked about "connectors to
  everything." Recommendation given: a local-folder picker fits the
  current zero-backend architecture, but real API connectors need
  either client-side secrets (insecure) or a backend proxy to hold
  credentials — a different scope than "single static HTML file." Not
  started; revisit only when the user picks a backend approach.
- **CLAUDE.md / PROJECT_MEMORY.md** (this file): created retroactively
  at the user's request after they referenced them as if they already
  existed. They didn't exist in this repo or `TheApostol/polkorp` before
  this commit — this is the first version.
