# POLKORP AI

> Opening the world of AI for you.
> No restrictions. No logs. No filters. Just you.
>
> **A Simple Corp.**

POLKORP AI is a private, self-hosted multi-AI orchestration platform. You
type what you want in plain language; the dashboard routes it to the right
local AI tool — code, image generation, image restoration/upscaling, or a
chained pipeline across several tools. Nothing runs in someone else's
cloud unless you choose to run it there (Kaggle/HF Spaces are optional
free-tier overflow compute, not a requirement).

**Philosophy:** the user orchestrates. The AI executes. No AI decides
what you're allowed to ask for.

---

## Architecture

```
                         ┌─────────────────────────┐
                         │      dashboard.html      │
                         │  (single-file, offline)  │
                         │ login · router · agents  │
                         └────────────┬────────────┘
                                      │ HTTP (fetch, CORS)
                                      ▼
        ┌─────────────────────────────────────────────────────┐
        │              backend/app.py (FastAPI, :5050)          │
        │   agents: terminal, code (live via Ollama)            │
        │           image, restoration, upscaling, osint,       │
        │           orchestrate (honest "not available here")   │
        └──────┬───────────────┬───────────────┬───────────────┘
               │               │               │
               ▼               ▼               ▼
        ┌───────────┐   ┌───────────┐   ┌───────────┐
        │  ollama   │   │   lama    │   │  fooocus  │
        │  :11434   │   │  cleaner  │   │  :7865    │
        │  (GPU)    │   │  :8080    │   │  (GPU)    │
        │           │   │  (GPU)    │   │           │
        └───────────┘   └───────────┘   └───────────┘

  Overflow / free-tier compute (independent of the VPS above):
        ┌────────────────────┐      ┌───────────────────────────┐
        │ Kaggle GPU notebook │      │  HF Spaces (Gradio demo)   │
        │ Ollama+Lama+Fooocus │      │  router simulation only    │
        └────────────────────┘      └───────────────────────────┘
```

The `image`/`restoration`/`upscaling`/`osint` agents are only "live" once
their tool is actually deployed and wired into `backend/app.py` (currently
just `code` and `terminal` are live, since only Ollama runs by default) —
they respond honestly that they need GPU tools instead of pretending to
work.

## Files in this repo

| File | Purpose |
|---|---|
| `dashboard.html` | The master dashboard. Single HTML file, zero dependencies, works offline, calls the backend for live agents when reachable. |
| `backend/app.py` | FastAPI backend defining the platform's agents (Code, Terminal Chat live via Ollama; others honest-unavailable) and `/api/status`. |
| `backend/requirements.txt` | Backend Python deps (fastapi, uvicorn, httpx, psutil). |
| `install-mac-light.sh` | Lightweight local installer (Ollama + Lama Cleaner) for low-spec Macs. |
| `deploy-vps-full.sh` | Full production deploy for an Ubuntu 22.04 + NVIDIA GPU VPS. |
| `docker-compose.yml` | The 5-service GPU stack `deploy-vps-full.sh` brings up. |
| `deploy-vps-free.sh` | Free-tier deploy for a CPU-only Oracle Always Free (or similar) VPS. |
| `docker-compose.free.yml` | The 3-service CPU-only stack `deploy-vps-free.sh` brings up. |
| `fooocus/Dockerfile` | Build context for the `fooocus` compose service (GPU stack only). |
| `kaggle-gpu-notebook.ipynb` | Runs Ollama + Lama Cleaner + Fooocus on Kaggle's free T4 GPU. |
| `huggingface-orchestrator/app.py` | Gradio demo of the router logic, deployable to HF Spaces for free. |
| `polkorpai.html` | An earlier, standalone dashboard build (kept as-is, not superseded). |

## Quick start

### Option A — MacBook (light, local only)

For low-spec Macs (this was written against a 2013 MacBook Air, 4GB RAM):

```bash
chmod +x install-mac-light.sh
./install-mac-light.sh
~/polkorp-ai/start.sh
```

Installs Ollama and Lama Cleaner directly on the Mac (via `pipx`, avoiding
the "externally-managed-environment" pip error on modern macOS Pythons).
No Docker, no GPU required — just enough to chat with a local LLM and
inpaint images.

### Option B — VPS (full production stack)

For an Ubuntu 22.04 server with an NVIDIA GPU:

```bash
scp dashboard.html docker-compose.yml deploy-vps-full.sh your-server:/root/
scp -r fooocus your-server:/root/
ssh your-server
sudo bash deploy-vps-full.sh
```

This installs Docker, the NVIDIA Container Toolkit, brings up all 5
containers (dashboard, backend stub, ollama, lama, fooocus), opens the
firewall (22/80/443/5050), and pulls the base models.

> **Note:** the `backend` service runs the real `backend/app.py` FastAPI
> app. `Code` and `Terminal Chat` are live (backed by Ollama); `Image`,
> `Restoration`, `Upscaling`, and `OSINT` currently respond that they
> need tools this VPS doesn't have installed, rather than pretending to
> work — wire up `lama`/`fooocus` (GPU stack only) or extend `app.py` to
> make more agents live.

### Option B2 — VPS (free-tier, CPU-only)

For a free CPU-only VPS (e.g. Oracle Cloud Always Free, no GPU):

```bash
scp dashboard.html docker-compose.free.yml deploy-vps-free.sh your-server:/root/
scp -r backend your-server:/root/
ssh your-server
sudo bash deploy-vps-free.sh
```

Brings up 3 containers (dashboard, backend, ollama — no lama/fooocus,
since those need GPU tooling this path doesn't have). `Code` and
`Terminal Chat` agents work for real, CPU-inference (slow but
functional); other agent categories tell you honestly they need the
Kaggle GPU notebook instead.

### Option C — Free-tier cloud compute

- **Kaggle**: upload `kaggle-gpu-notebook.ipynb`, enable GPU T4 x2 +
  Internet in the notebook settings, run all cells. Gives you Ollama +
  Lama Cleaner + a public Fooocus link, no ngrok needed, for up to
  ~9-12h per session within your 30h/week quota.
- **Hugging Face Spaces**: create a new Space (SDK: Gradio), upload
  `huggingface-orchestrator/app.py` plus a `requirements.txt` containing
  `gradio`. This deploys a public demo of the router logic — useful for
  showing the orchestration concept, not for running the actual tools
  (those need real GPU compute, which free Spaces CPU tier doesn't have).

## Dashboard usage

1. Open `dashboard.html` in a browser (works fully offline, `file://` included).
2. Enter the access code (stored only as a SHA-256 hash in the file —
   never in plaintext).
3. Type what you want in the command prompt and press Enter, or click
   through the card grid directly.
4. `1`-`6` opens a card, `/` focuses the prompt, `` ` `` toggles the
   terminal panel, `Esc` closes whatever's open.

## AI Router + Agents

The router scans your input for keywords and picks a category. If more
than one category matches (or the input mentions "audit"/"review"/
"chain"), it switches to **pipeline mode** and shows a simulated
step-by-step chain (no orchestration engine calls multiple agents yet —
each step still needs to be run as its own single request today).

| Keywords contain... | Category | Backend agent | Live? |
|---|---|---|---|
| code, exploit, virus, script, payload | Code | `code` | ✅ via Ollama |
| image, generate, draw, art | Image | `image` | ❌ needs GPU (Fooocus) |
| clean, remove, inpaint | Restoration | `restoration` | ❌ needs Lama Cleaner |
| upscale, enhance, 4k | Upscaling | `upscaling` | ❌ needs Upscayl |
| hack, osint, recon | Hack/OSINT | `osint` | ❌ no toolchain deployed |
| audit, review, chain | Orchestrate | `orchestrate` | ❌ UI simulation only |
| *(no match)* | Terminal Chat | `terminal` | ✅ via Ollama |

For single-category requests, `dashboard.html` calls the live backend
agent for real via `POST /api/chat` and logs the reply in the terminal
panel (press `` ` `` to view it) plus a toast preview. Agents marked
"not live" return an honest explanation instead of a fabricated result.

The same category table is reimplemented in
`huggingface-orchestrator/app.py` for the HF Spaces demo — kept in sync
by hand, no shared build step between the JS and Python versions.

## API endpoints (backend/app.py)

- `GET /api/agents` — lists all agents and whether each is currently live.
- `POST /api/chat` — `{ "agent": "code", "message": "..." }` → calls the
  agent's Ollama system prompt if live, or returns its
  `unavailable_reason` if not.
- `GET /api/status` — powers the dashboard's VPS Status widget: RAM,
  Ollama reachability + loaded models, uptime. `dashboard.html` falls
  back to an honest "Awaiting deployment" state if this is unreachable
  (e.g. testing the file standalone via `file://`, or before deploy).

CORS is wide open (`allow_origins=["*"]`) since this is a private
single-user tool with no per-user auth — see Security notes below before
exposing it beyond your own use.

## Security notes

- The access code is a client-side gate (SHA-256 hash check via
  `crypto.subtle`), not a real authentication system. It stops casual
  access to the dashboard file; it does **not** protect the VPS itself.
  Don't expose the VPS's ports to the open internet without also putting
  real auth (or at minimum an IP allowlist / VPN) in front of them.
- `deploy-vps-full.sh` opens 22/80/443/5050 via UFW and installs
  `fail2ban`, but does not configure SSL — it deploys over plain HTTP.
  Put nginx behind certbot/Let's Encrypt once `polkorp.com`'s DNS points
  at the server.
- This is a single-user, private tool by design — there's no per-user
  auth, RBAC, or audit logging anywhere in this stack. Don't repurpose it
  as a multi-tenant service without adding all of that first.

## Keyboard shortcuts

| Key | Action |
|---|---|
| `1`-`6` | Open the corresponding card |
| `/` | Focus the command prompt |
| `` ` `` | Toggle the terminal panel |
| `Esc` | Close whatever panel/card is open |

## Troubleshooting

- **"externally-managed-environment" pip error on Mac**: this is exactly
  why `install-mac-light.sh` installs `lama-cleaner` via `pipx` instead
  of `pip install` directly — if you're doing something manually outside
  the script, use `pipx install <package>` instead of `pip install`.
- **`nvidia-smi` not found on the VPS**: `deploy-vps-full.sh` installs
  the *container* toolkit, not the host GPU driver. Install the NVIDIA
  driver for your GPU/distro first, then re-run the script.
- **Model pull fails during VPS deploy**: the script pulls
  `deepseek-coder-v2`, `llama3.1:8b`, `mistral`, `codeqwen` via Ollama.
  (The original plan listed `mistral-large` — that's Mistral's API-only
  flagship model with no local weights, so it can't be pulled through
  Ollama; `mistral` is the real local tag and is what the script uses.)
  If a pull fails, re-run `docker compose exec ollama ollama pull <model>`
  manually — it's often just a transient network blip.
- **Fooocus container fails to build**: `fooocus/Dockerfile` clones the
  upstream `lllyasviel/Fooocus` repo at build time, so it needs internet
  access during `docker compose up --build` and enough disk space for the
  models Fooocus downloads on first run.
- **Dashboard shows "Backend unreachable"**: `dashboard.html` calls the
  backend on port `5050` of whatever host it's served from — that port
  needs to be open both in the host firewall (`ufw`, handled by the
  deploy scripts) *and* in your cloud provider's own firewall/security
  list (e.g. Oracle Cloud Security Lists don't inherit from `ufw` —
  they're separate). Also give the `backend` container a minute on first
  boot; it runs `pip install` before starting.
- **Voice dictation errors "Microphone blocked"**: browsers only allow
  microphone access on HTTPS or `localhost`, never plain HTTP. This is a
  browser security policy, not a bug — it'll work once SSL/a domain is
  set up in front of the VPS, or when testing `dashboard.html` locally
  via `file://`.

---

*A Simple Corp.*
