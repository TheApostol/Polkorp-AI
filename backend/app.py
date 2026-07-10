"""
POLKORP AI — Backend

Defines the platform's distinct agents and exposes them over HTTP for
dashboard.html to call. Each agent has its own persona/system prompt.
Agents backed by Ollama (code, terminal) are live on any box running this
service. Agents that need GPU tools not installed on this box (image,
restoration, upscaling, osint) respond honestly that they're unavailable
here and point at the Kaggle GPU notebook instead of pretending to work.

A Simple Corp.
"""

import os
import time

import httpx
import psutil
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
        "live": False,
        "unavailable_reason": {
            "en": (
                "The OSINT/recon module isn't installed on this box yet — no "
                "tooling is wired up here. This category is a placeholder in "
                "the router until a real OSINT toolchain is deployed."
            ),
            "es": (
                "El módulo de OSINT/recon todavía no está instalado en este "
                "servidor. Esta categoría es un placeholder en el router "
                "hasta que se despliegue un toolchain de OSINT real."
            ),
        },
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


class ChatRequest(BaseModel):
    agent: str
    message: str
    lang: str = "en"


@app.get("/api/agents")
def list_agents():
    return {
        key: {"name": a["name"], "live": a["live"]}
        for key, a in AGENTS.items()
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    lang = req.lang if req.lang in LANG_INSTRUCTION else "en"
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
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": req.message,
                    "system": system_prompt,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "agent": agent["name"],
                "live": True,
                "reply": data.get("response", "").strip() or "(empty response)",
            }
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        detail = (
            f"Couldn't reach Ollama ({OLLAMA_MODEL}) — it may still be "
            f"loading the model on this CPU-only box, or the pull "
            f"never finished. Details: {exc}"
            if lang == "en" else
            f"No se pudo conectar con Ollama ({OLLAMA_MODEL}) — puede que "
            f"todavía esté cargando el modelo en este servidor sin GPU, o "
            f"que la descarga nunca haya terminado. Detalles: {exc}"
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
