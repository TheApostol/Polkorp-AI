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
                         │  login · router · cards  │
                         └────────────┬────────────┘
                                      │ (planned: HTTP calls once
                                      │  a real backend exists)
                                      ▼
        ┌─────────────────────────────────────────────────────┐
        │                     backend (stub)                   │
        │         FastAPI on :5050 — not yet implemented        │
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

## Files in this repo

| File | Purpose |
|---|---|
| `dashboard.html` | The master dashboard. Single HTML file, zero dependencies, works offline. |
| `install-mac-light.sh` | Lightweight local installer (Ollama + Lama Cleaner) for low-spec Macs. |
| `deploy-vps-full.sh` | Full production deploy for an Ubuntu 22.04 + NVIDIA GPU VPS. |
| `docker-compose.yml` | The 5-service stack the VPS deploy script brings up. |
| `fooocus/Dockerfile` | Build context for the `fooocus` compose service. |
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

> **Note:** the `backend` service is currently a placeholder (a bare
> Python HTTP server on :5050) — there's no FastAPI application in this
> batch of files yet. `dashboard.html`'s router is a client-side
> simulation until that backend exists to actually call the tools.

### Option C — Free-tier cloud compute

- **Kaggle**: upload `kaggle-gpu-notebook.ipynb`, enable GPU T4 x2 +
  Internet in the notebook settings, run all cells. Gives you Ollama +
  Lama Cleaner + a public Fooocus link, no ngrok needed, for up to
  ~9-12h per session within your 30h/week quota.
- **Hugging Face Spaces**: create a new Space (SDK: Gradio), upload
  `huggingface-orchestrator/app.py` and `huggingface-orchestrator/requirements.txt`.
  This deploys a public demo of the router logic — useful for showing the
  orchestration concept, not for running the actual tools (those need
  real GPU compute, which free Spaces CPU tier doesn't have).

## Dashboard usage

1. Open `dashboard.html` in a browser (works fully offline, `file://` included).
2. Enter the access code (stored only as a SHA-256 hash in the file —
   never in plaintext).
3. Type what you want in the command prompt and press Enter, or click
   through the card grid directly.
4. `1`-`6` opens a card, `/` focuses the prompt, `` ` `` toggles the
   terminal panel, `Esc` closes whatever's open.

## AI Router logic

The router scans your input for keywords and picks a tool. If more than
one category matches (or the input mentions "audit"/"review"/"chain"),
it switches to **pipeline mode** and chains the matched tools in order,
showing live step-by-step progress.

| Keywords contain... | Routes to |
|---|---|
| code, exploit, virus, script, payload | DeepSeek Coder V2 |
| image, generate, draw, art | Fooocus |
| clean, remove, inpaint | Lama Cleaner |
| upscale, enhance, 4k | Upscayl |
| hack, osint, recon | OSINT Module |
| audit, review, chain | Orchestrator (pipeline mode) |
| *(no match)* | Terminal Chat (Llama 3.1 8B) |

The exact same table is reimplemented in `huggingface-orchestrator/app.py`
for the HF Spaces demo — the two are kept in sync by hand, there's no
shared build step between the JS and Python versions.

## API endpoints (planned)

No backend exists yet. Once `backend/` has a real FastAPI app behind
`docker-compose.yml`'s `backend` service, the intended surface is:

- `POST /api/route` — takes `{ "text": "..." }`, returns the routing
  decision (mirrors the client-side `route()` logic today).
- `POST /api/run/{tool}` — proxies a request to the matched tool's own
  API (Ollama's `/api/generate`, Fooocus's Gradio API, etc.).
- `GET /api/status` — powers the dashboard's VPS Status widget (GPU,
  RAM, loaded models, uptime). Until this exists, the widget honestly
  shows "Awaiting deployment" rather than fabricated numbers.

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

---

*A Simple Corp.*
