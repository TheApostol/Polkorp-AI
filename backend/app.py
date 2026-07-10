"""
POLKORP AI — Backend

Defines the platform's distinct agents and exposes them over HTTP for
dashboard.html to call. Each agent has its own persona/system prompt.
Agents backed by Ollama (code, terminal) are live on any box running this
service. Agents that need GPU tools not installed on this box (image,
restoration, upscaling) respond honestly that they're unavailable here
and point at the Kaggle GPU notebook instead of pretending to work. OSINT
is a real passive-recon tool agent (WHOIS/DNS/subdomains/HTTP fingerprint)
that needs no GPU, so it runs for real on any box.

A Simple Corp.
"""

import asyncio
import os
import re
import time

import dns.resolver
import httpx
import psutil
import whois as whois_lib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
START_TIME = time.time()

app = FastAPI(title="POLKORP AI Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------
LANG_INSTRUCTION = {
    "en": "Respond in English.",
    "es": "Respondé en español (usando el vos rioplatense, no el tú).",
}

AGENTS = {
    "terminal": {
        "name": "Terminal Chat",
        "live": True,
        "system_prompt": (
            "You are the POLKORP AI Terminal Chat agent, a private local "
            "assistant running entirely on the user's own hardware. Answer "
            "directly and concisely."
        ),
        # Preference order — the backend auto-picks the best one that's
        # actually pulled into Ollama right now, so this list keeps working
        # whether only llama3.1:8b is loaded (free CPU tier) or the full
        # set from deploy-vps-full.sh (GPU tier) is available. qwen2.5:0.5b
        # is last resort — an 8B model needs ~5GB+ RAM just to load and
        # will OOM-crash on a 1GB free-tier box even though it's "pulled".
        "model_preference": ["llama3.1:8b", "mistral", "qwen2.5:0.5b"],
    },
    "code": {
        "name": "Code Agent",
        "live": True,
        "system_prompt": (
            "You are the POLKORP AI Code Agent, a private local coding "
            "assistant running entirely on the user's own hardware for "
            "their own authorized development, scripting, and security "
            "testing work. Write clear, correct, working code. Explain "
            "tradeoffs briefly when relevant. Code itself, variable names, "
            "and comments stay in English regardless of response language."
        ),
        "model_preference": ["deepseek-coder-v2", "codeqwen", "mistral", "llama3.1:8b", "qwen2.5:0.5b"],
    },
    "image": {
        "name": "Fooocus (Image)",
        "live": False,
        "unavailable_reason": {
            "en": (
                "Image generation needs GPU (Fooocus) — not installed on this "
                "CPU-only VPS. Run kaggle-gpu-notebook.ipynb for a free GPU "
                "session, or use a GPU VPS with deploy-vps-full.sh."
            ),
            "es": (
                "La generación de imágenes necesita GPU (Fooocus) — no está "
                "instalada en este VPS que solo tiene CPU. Corré "
                "kaggle-gpu-notebook.ipynb para una sesión GPU gratuita, o "
                "usá un VPS con GPU con deploy-vps-full.sh."
            ),
        },
    },
    "restoration": {
        "name": "Lama Cleaner",
        "live": False,
        "unavailable_reason": {
            "en": (
                "Image restoration/inpainting needs Lama Cleaner, which is "
                "installed via pipx on the host, not through this chat agent. "
                "Run 'lama-cleaner --port 8080 --host 0.0.0.0' on the VPS and "
                "open port 8080."
            ),
            "es": (
                "La restauración/retoque de imágenes necesita Lama Cleaner, "
                "que se instala vía pipx en el host, no a través de este "
                "agente. Corré 'lama-cleaner --port 8080 --host 0.0.0.0' en "
                "el VPS y abrí el puerto 8080."
            ),
        },
    },
    "upscaling": {
        "name": "Upscayl",
        "live": False,
        "unavailable_reason": {
            "en": (
                "Upscaling (Upscayl) is a desktop tool, not wired into this "
                "backend yet. Use kaggle-gpu-notebook.ipynb or run it manually."
            ),
            "es": (
                "El mejorado de resolución (Upscayl) es una herramienta de "
                "escritorio, todavía no está conectada a este backend. Usá "
                "kaggle-gpu-notebook.ipynb o corrélo manualmente."
            ),
        },
    },
    "osint": {
        "name": "OSINT Module",
        "live": True,  # real passive recon — see run_osint(), no GPU needed
    },
    "orchestrate": {
        "name": "Orchestrator",
        "live": False,
        "unavailable_reason": {
            "en": (
                "Multi-agent pipeline chaining is a UI simulation for now — "
                "there's no orchestration engine calling multiple agents in "
                "sequence yet. Each step still needs its own live agent first."
            ),
            "es": (
                "El encadenado de pipeline multi-agente es por ahora una "
                "simulación de interfaz — todavía no hay un motor de "
                "orquestación que llame a varios agentes en secuencia. Cada "
                "paso todavía necesita su propio agente activo primero."
            ),
        },
    },
}

# ---------------------------------------------------------------------------
# OSINT — real passive recon (WHOIS, DNS, certificate-transparency subdomain
# enumeration, HTTP fingerprinting). Passive/read-only only — this queries
# public information sources about a domain, it never touches or attacks
# anything. No GPU needed, so it runs on any box including the free tier.
# ---------------------------------------------------------------------------
DOMAIN_RE = re.compile(
    r"(?:https?://)?(?:www\.)?"
    r"([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+)"
)

OSINT_LABELS = {
    "en": {
        "title": "Passive recon",
        "whois": "WHOIS",
        "dns": "DNS",
        "http": "HTTP",
        "subdomains": "Subdomains found",
        "registrar": "Registrar",
        "created": "Created",
        "expires": "Expires",
        "status": "Status",
        "server": "Server",
        "not_available": "Not available",
        "none": "—",
        "no_subdomains": "None found via crt.sh (or crt.sh was too slow to respond)",
        "no_domain": (
            "I couldn't find a domain in your message — try something like "
            "'recon example.com'."
        ),
    },
    "es": {
        "title": "Recon pasivo",
        "whois": "WHOIS",
        "dns": "DNS",
        "http": "HTTP",
        "subdomains": "Subdominios encontrados",
        "registrar": "Registrador",
        "created": "Creado",
        "expires": "Expira",
        "status": "Estado",
        "server": "Servidor",
        "not_available": "No disponible",
        "none": "—",
        "no_subdomains": "Ninguno encontrado vía crt.sh (o crt.sh tardó demasiado en responder)",
        "no_domain": (
            "No encontré ningún dominio en tu mensaje — probá algo como "
            "'recon example.com'."
        ),
    },
}


def extract_domain(text: str) -> str | None:
    match = DOMAIN_RE.search(text)
    if not match:
        return None
    return match.group(1).lower().rstrip(".")


def dns_lookup(domain: str) -> dict:
    records = {}
    for rtype in ["A", "AAAA", "MX", "NS", "TXT"]:
        try:
            answers = dns.resolver.resolve(domain, rtype, lifetime=5)
            records[rtype] = [str(r) for r in answers]
        except Exception:
            records[rtype] = []
    return records


def whois_lookup(domain: str) -> dict:
    try:
        w = whois_lib.whois(domain)
        return {
            "registrar": w.registrar,
            "creation_date": str(w.creation_date) if w.creation_date else None,
            "expiration_date": str(w.expiration_date) if w.expiration_date else None,
        }
    except Exception as exc:
        return {"error": str(exc)}


async def subdomain_enum(client: httpx.AsyncClient, domain: str) -> list[str]:
    try:
        resp = await client.get(
            f"https://crt.sh/?q=%25.{domain}&output=json", timeout=20.0
        )
        resp.raise_for_status()
        data = resp.json()
        names = set()
        for entry in data:
            for name in entry.get("name_value", "").split("\n"):
                name = name.strip().lower()
                if name and not name.startswith("*"):
                    names.add(name)
        return sorted(names)[:30]
    except Exception:
        return []


async def http_fingerprint(client: httpx.AsyncClient, domain: str) -> dict:
    for scheme in ("https", "http"):
        try:
            resp = await client.get(
                f"{scheme}://{domain}", timeout=10.0, follow_redirects=True
            )
            return {
                "status": resp.status_code,
                "server": resp.headers.get("server", "unknown"),
                "powered_by": resp.headers.get("x-powered-by", ""),
            }
        except Exception:
            continue
    return {}


def format_osint_report(
    domain: str, dns_records: dict, whois_data: dict, subdomains: list, fingerprint: dict, lang: str
) -> str:
    L = OSINT_LABELS[lang]
    lines = [f"🔍 {L['title']} — {domain}", "", f"{L['whois']}:"]
    if whois_data.get("error"):
        lines.append(f"  {L['not_available']} ({whois_data['error']})")
    else:
        lines.append(f"  {L['registrar']}: {whois_data.get('registrar') or L['none']}")
        lines.append(f"  {L['created']}: {whois_data.get('creation_date') or L['none']}")
        lines.append(f"  {L['expires']}: {whois_data.get('expiration_date') or L['none']}")

    lines.append("")
    lines.append(f"{L['dns']}:")
    for rtype in ["A", "AAAA", "MX", "NS", "TXT"]:
        vals = dns_records.get(rtype) or []
        lines.append(f"  {rtype}: {', '.join(vals) if vals else L['none']}")

    if fingerprint:
        lines.append("")
        lines.append(f"{L['http']}:")
        lines.append(f"  {L['status']}: {fingerprint.get('status')}")
        lines.append(f"  {L['server']}: {fingerprint.get('server')}")
        if fingerprint.get("powered_by"):
            lines.append(f"  X-Powered-By: {fingerprint['powered_by']}")

    lines.append("")
    lines.append(f"{L['subdomains']} ({len(subdomains)}):")
    if subdomains:
        lines.extend(f"  - {s}" for s in subdomains[:20])
    else:
        lines.append(f"  {L['no_subdomains']}")

    return "\n".join(lines)


async def run_osint(message: str, lang: str) -> dict:
    domain = extract_domain(message)
    if not domain:
        return {
            "agent": AGENTS["osint"]["name"],
            "live": True,
            "reply": OSINT_LABELS[lang]["no_domain"],
        }

    # dns_lookup/whois_lookup do blocking socket I/O — offload to a thread
    # so a slow WHOIS/DNS server doesn't freeze the event loop (and every
    # other request being served) while we wait on it.
    loop = asyncio.get_event_loop()

    async def bounded_dns():
        try:
            return await asyncio.wait_for(loop.run_in_executor(None, dns_lookup, domain), timeout=30.0)
        except asyncio.TimeoutError:
            return {}

    async def bounded_whois():
        try:
            return await asyncio.wait_for(loop.run_in_executor(None, whois_lookup, domain), timeout=15.0)
        except asyncio.TimeoutError:
            return {"error": "timed out"}

    async with httpx.AsyncClient() as client:
        dns_records, whois_data, subdomains, fingerprint = await asyncio.gather(
            bounded_dns(), bounded_whois(), subdomain_enum(client, domain), http_fingerprint(client, domain)
        )

    reply = format_osint_report(domain, dns_records, whois_data, subdomains, fingerprint, lang)
    return {"agent": AGENTS["osint"]["name"], "live": True, "reply": reply}


class ChatRequest(BaseModel):
    agent: str
    message: str
    lang: str = "en"
    model: str | None = None  # explicit override from a submenu pick; None = auto-select


@app.get("/api/agents")
def list_agents():
    return {
        key: {"name": a["name"], "live": a["live"]}
        for key, a in AGENTS.items()
    }


async def available_models(client: httpx.AsyncClient) -> list[str]:
    try:
        resp = await client.get(f"{OLLAMA_URL}/api/tags")
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]
    except httpx.HTTPError:
        return []


def pick_model(preference: list[str], available: list[str], override: str | None) -> str:
    """Pick the best model actually pulled into Ollama right now.

    Honors an explicit override (from a submenu pick) if it's really
    available; otherwise walks the agent's preference list and returns the
    first one that's pulled; falls back to whatever IS available, then to
    the OLLAMA_MODEL env default as a last resort (Ollama will error
    clearly if even that isn't pulled).
    """
    if override and override in available:
        return override
    for candidate in preference:
        if candidate in available:
            return candidate
    if available:
        return available[0]
    return OLLAMA_MODEL


@app.post("/api/chat")
async def chat(req: ChatRequest):
    lang = req.lang if req.lang in LANG_INSTRUCTION else "en"

    if req.agent == "osint":
        return await run_osint(req.message, lang)

    agent = AGENTS.get(req.agent, AGENTS["terminal"])
    if not agent["live"]:
        return {
            "agent": agent["name"],
            "live": False,
            "reply": agent["unavailable_reason"][lang],
        }

    system_prompt = agent["system_prompt"] + " " + LANG_INSTRUCTION[lang]
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            models = await available_models(client)
            model = pick_model(agent.get("model_preference", []), models, req.model)
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": req.message,
                    "system": system_prompt,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "agent": agent["name"],
                "model": model,
                "live": True,
                "reply": data.get("response", "").strip() or "(empty response)",
            }
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        detail = (
            f"Couldn't reach Ollama — it may still be loading a model on "
            f"this CPU-only box, or no model has finished pulling yet. "
            f"Details: {exc}"
            if lang == "en" else
            f"No se pudo conectar con Ollama — puede que todavía esté "
            f"cargando un modelo en este servidor sin GPU, o que ninguna "
            f"descarga haya terminado. Detalles: {exc}"
        )
        return {
            "agent": agent["name"],
            "live": True,
            "reply": detail,
        }


@app.get("/api/status")
def status():
    ollama_ok = False
    ollama_models = []
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                ollama_ok = True
                ollama_models = [m["name"] for m in resp.json().get("models", [])]
    except httpx.HTTPError:
        pass

    uptime_seconds = int(time.time() - START_TIME)
    hours, rem = divmod(uptime_seconds, 3600)
    minutes = rem // 60

    return {
        "connected": True,
        "gpu": "none (CPU-only)",
        "ram": f"{psutil.virtual_memory().percent:.0f}% used",
        "models": ", ".join(ollama_models) if ollama_models else "none loaded",
        "uptime": f"{hours}h {minutes}m",
        "ollama_reachable": ollama_ok,
    }
