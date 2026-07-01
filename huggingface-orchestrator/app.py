"""
POLKORP AI — Orchestrator (Hugging Face Spaces demo)

Simulates the same natural-language AI Router used by dashboard.html.
Takes free-text input, decides which tool(s) it would route to, and
streams the routing decision the same way the dashboard's toast/pipeline
UI does. This is a router simulation for demoing the orchestration
concept on free HF Spaces compute — it does not call the actual tools
(Ollama/Fooocus/Lama Cleaner/Upscayl live on the user's own VPS/Mac, not
inside this Space).

Opening the world of AI for you.
A Simple Corp.
"""

import time

import gradio as gr

# ---------------------------------------------------------------------------
# Router table — keep in sync with dashboard.html's ROUTES array manually;
# there's no shared build step between the JS and Python versions.
# ---------------------------------------------------------------------------
ROUTES = [
    {
        "category": "Code",
        "tool": "DeepSeek Coder V2",
        "keywords": ["code", "exploit", "virus", "script", "payload"],
    },
    {
        "category": "Image",
        "tool": "Fooocus",
        "keywords": ["image", "generate", "draw", "art"],
    },
    {
        "category": "Restoration",
        "tool": "Lama Cleaner",
        "keywords": ["clean", "remove", "inpaint"],
    },
    {
        "category": "Upscaling",
        "tool": "Upscayl",
        "keywords": ["upscale", "enhance", "4k"],
    },
    {
        "category": "Hack/OSINT",
        "tool": "OSINT Module",
        "keywords": ["hack", "osint", "recon"],
    },
    {
        "category": "Orchestrate",
        "tool": "Orchestrator",
        "keywords": ["audit", "review", "chain"],
    },
]

DEFAULT_ROUTE = {"category": "Terminal Chat", "tool": "Terminal Chat (Llama 3.1 8B)"}


def route(text: str):
    """Return the list of matching routes for the given input, in table order."""
    lowered = text.lower()
    matches = []
    for entry in ROUTES:
        if any(keyword in lowered for keyword in entry["keywords"]):
            matches.append(entry)
    return matches


def orchestrate(message: str, history):
    """Generator driving the Gradio chat-style streaming response."""
    if not message or not message.strip():
        yield "Type something for POLKORP AI to orchestrate."
        return

    yield "🧠 Analyzing..."
    time.sleep(0.6)

    matches = route(message)

    if not matches:
        yield f"🧠 Analyzing...\n\n⚡ Orchestrating: {DEFAULT_ROUTE['tool']}"
        time.sleep(0.7)
        yield (
            f"🧠 Analyzing...\n\n⚡ Orchestrating: {DEFAULT_ROUTE['tool']}\n\n"
            "✅ Done — this is a routing simulation. Connect your VPS/Mac "
            "backend to actually run the tool."
        )
        return

    pipeline_mode = len(matches) > 1 or matches[0]["category"] == "Orchestrate"

    if pipeline_mode:
        tools = [m["tool"] for m in matches]
        progress_lines = ["🧠 Analyzing...", "", "⛓ PIPELINE ORCHESTRATOR"]
        yield "\n".join(progress_lines)
        for i, tool in enumerate(tools):
            time.sleep(0.6)
            step_lines = list(progress_lines)
            for j, t in enumerate(tools):
                if j < i:
                    step_lines.append(f"  [✓] {t}")
                elif j == i:
                    step_lines.append(f"  [⟳] {t}")
                else:
                    step_lines.append(f"  [ ] {t}")
            yield "\n".join(step_lines)
        time.sleep(0.4)
        final_lines = list(progress_lines) + [f"  [✓] {t}" for t in tools]
        final_lines.append("")
        final_lines.append("✅ Done — pipeline simulation complete.")
        yield "\n".join(final_lines)
        return

    tool = matches[0]["tool"]
    category = matches[0]["category"]
    yield f"🧠 Analyzing...\n\n⚡ Orchestrating: {tool} ({category})"
    time.sleep(0.7)
    yield (
        f"🧠 Analyzing...\n\n⚡ Orchestrating: {tool} ({category})\n\n"
        "✅ Done — this is a routing simulation. Connect your VPS/Mac "
        "backend to actually run the tool."
    )


# ---------------------------------------------------------------------------
# Dark theme matching the POLKORP AI palette.
# ---------------------------------------------------------------------------
POLKORP_CSS = """
:root {
    --primary: #00d4ff;
    --secondary: #0066ff;
    --success: #00ff88;
    --error: #ff3333;
}
body, .gradio-container { background: #0a0a0f !important; }
.gradio-container * { font-family: 'SF Mono', 'Fira Code', 'Courier New', monospace !important; }
#title { color: var(--primary); letter-spacing: .1em; }
"""

theme = gr.themes.Base(
    primary_hue="cyan",
    secondary_hue="blue",
    neutral_hue="slate",
).set(
    body_background_fill="#0a0a0f",
    block_background_fill="#0f0f1a",
    border_color_primary="#ffffff10",
)

with gr.Blocks(theme=theme, css=POLKORP_CSS, title="POLKORP AI — Orchestrator") as demo:
    gr.Markdown(
        "# ◈ POLKORP AI — Orchestrator\n"
        "Opening the world of AI for you. No restrictions. No logs. No filters. Just you.\n\n"
        "_A Simple Corp._",
        elem_id="title",
    )
    gr.ChatInterface(
        fn=orchestrate,
        type="messages",
        textbox=gr.Textbox(
            placeholder="What do you want to orchestrate?",
            container=False,
        ),
        examples=[
            "Write a Python exploit for testing",
            "Generate a cyberpunk city",
            "Clean this image and upscale to 4K",
            "Audit and chain multiple tools",
        ],
    )

if __name__ == "__main__":
    demo.queue().launch()
