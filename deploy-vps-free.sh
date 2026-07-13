#!/usr/bin/env bash
#
# POLKORP AI — Free-tier VPS deployment (Oracle Cloud Always Free)
# Target: Ubuntu 22.04, ARM64 (Ampere A1, VM.Standard.A1.Flex), 2 OCPU / 12GB
#         RAM, NO GPU.
#
# This is the CPU-only counterpart to deploy-vps-full.sh. Use this when
# you're on a free ARM instance with no NVIDIA GPU. Ollama runs CPU-only
# (fine for small/medium quantized models); Lama Cleaner installs via pipx
# directly on the host instead of Docker (the cwq1913/lama-cleaner image's
# ARM64 support is unverified); Fooocus is not deployed here at all — route
# image generation to a Kaggle GPU session instead (kaggle-gpu-notebook.ipynb).
#
# Run as root or via sudo: sudo bash deploy-vps-free.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[*]${NC} $1"; }
ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1" >&2; }
fatal() { err "$1"; exit 1; }

POLKORP_DIR="/opt/polkorp"

echo -e "${BOLD}${CYAN}"
echo "╔══════════════════════════════════════════╗"
echo "║   POLKORP AI — Free-Tier VPS Deployment   ║"
echo "║        Opening the world of AI for you.   ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ---------------------------------------------------------------------------
# 0. Root + OS + arch check
# ---------------------------------------------------------------------------
if [[ "${EUID}" -ne 0 ]]; then
  fatal "Run this as root: sudo bash deploy-vps-free.sh"
fi
if ! grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
  warn "This script targets Ubuntu 22.04 — proceeding anyway, but expect surprises on other distros."
fi
ARCH="$(uname -m)"
info "Architecture: ${ARCH}"
if [[ "${ARCH}" != "aarch64" && "${ARCH}" != "arm64" ]]; then
  warn "Expected ARM64 (Oracle Ampere A1) but detected ${ARCH}. If this is actually an x86_64 GPU box, use deploy-vps-full.sh instead."
fi

# ---------------------------------------------------------------------------
# 1. System update + base packages
# ---------------------------------------------------------------------------
info "Updating apt and installing base packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y curl wget git python3-pip python3-venv pipx ufw fail2ban ca-certificates gnupg
ok "Base packages installed"

# ---------------------------------------------------------------------------
# 2. Docker + Docker Compose plugin
# ---------------------------------------------------------------------------
if command -v docker >/dev/null 2>&1; then
  ok "Docker already installed: $(docker --version)"
else
  info "Installing Docker..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
  ok "Docker installed: $(docker --version)"
fi

# ---------------------------------------------------------------------------
# 3. /opt/polkorp scaffold + docker-compose.free.yml
# ---------------------------------------------------------------------------
info "Creating ${POLKORP_DIR}..."
mkdir -p "${POLKORP_DIR}"/{dashboard,backend}

if [[ -f "$(dirname "$0")/docker-compose.free.yml" ]]; then
  cp "$(dirname "$0")/docker-compose.free.yml" "${POLKORP_DIR}/docker-compose.yml"
  ok "Copied docker-compose.free.yml -> ${POLKORP_DIR}/docker-compose.yml"
else
  fatal "docker-compose.free.yml not found next to this script. Copy it into $(dirname "$0") and re-run."
fi

if [[ -f "$(dirname "$0")/dashboard.html" ]]; then
  cp "$(dirname "$0")/dashboard.html" "${POLKORP_DIR}/dashboard/index.html"
  ok "Copied dashboard.html into ${POLKORP_DIR}/dashboard/index.html"
else
  warn "dashboard.html not found next to this script — the dashboard container will have nothing to serve until you copy it in."
fi

# ---------------------------------------------------------------------------
# 4. Lama Cleaner via pipx (host-level, not Docker — see header note)
# ---------------------------------------------------------------------------
info "Installing Lama Cleaner via pipx..."
if command -v lama-cleaner >/dev/null 2>&1; then
  ok "Lama Cleaner already installed"
else
  pipx install lama-cleaner || warn "Lama Cleaner install failed — check 'pipx runpip lama-cleaner list' for details. Not fatal, rest of the stack still works."
  pipx ensurepath || true
fi

# ---------------------------------------------------------------------------
# 5. Firewall — cloud-level Security List rules must ALSO be added in the
#    Oracle console; this only handles the host's own iptables/ufw.
# ---------------------------------------------------------------------------
info "Configuring UFW..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 5050/tcp
ufw allow 8080/tcp   # Lama Cleaner
ufw --force enable
ok "UFW enabled: 22, 80, 443, 5050, 8080 open"
warn "Oracle Cloud also enforces a Security List firewall at the cloud level — add the same ports there via the console, or this host stays unreachable regardless of ufw."

# ---------------------------------------------------------------------------
# 6. Bring the Docker stack up
# ---------------------------------------------------------------------------
if systemctl is-active --quiet nginx 2>/dev/null; then
  warn "Host nginx is running and would block the dashboard container's port 80 — stopping it."
  systemctl stop nginx
  systemctl disable nginx
fi
info "Starting containers via docker compose..."
(cd "${POLKORP_DIR}" && docker compose up -d)
ok "Stack is up (dashboard, backend, ollama)"

# ---------------------------------------------------------------------------
# 7. Pull a small model. This host has no GPU; RAM varies a lot by which
#    free-tier shape you actually got approved for. An 8B model (llama3.1,
#    mistral) needs ~5GB+ RAM just to load — on a 1GB E2.1.Micro box it
#    pulls successfully but OOM-crashes on every single inference request
#    (confirmed: "ggml_aligned_malloc: insufficient memory"). qwen2.5:0.5b
#    (~400MB) actually runs on a 1GB box. If you're on a bigger free-tier
#    shape (e.g. 12GB Ampere A1), feel free to also pull llama3.1:8b
#    manually afterward — it'll be picked automatically once pulled, since
#    backend/app.py auto-selects the best model that's actually loadable.
# ---------------------------------------------------------------------------
info "Pulling huihui_ai/qwen2.5-abliterate:0.5b into Ollama (uncensored, ~400MB, runs on low-RAM free-tier boxes)..."
if docker compose -f "${POLKORP_DIR}/docker-compose.yml" exec -T ollama ollama pull huihui_ai/qwen2.5-abliterate:0.5b; then
  ok "huihui_ai/qwen2.5-abliterate:0.5b pulled"
else
  warn "Model pull failed — check 'docker compose logs ollama' and retry manually later."
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
PUBLIC_IP=$(curl -fsSL ifconfig.me 2>/dev/null || echo "<your-server-ip>")
echo ""
echo -e "${GREEN}${BOLD}POLKORP AI free-tier deployment complete.${NC}"
echo -e "  Dashboard:    ${CYAN}http://${PUBLIC_IP}/${NC}"
echo -e "  Backend:      ${CYAN}http://${PUBLIC_IP}:5050/${NC}"
echo -e "  Ollama:       ${CYAN}http://${PUBLIC_IP}:11434/${NC} (CPU-only)"
echo -e "  Lama Cleaner: ${CYAN}run 'lama-cleaner --port 8080 --host 0.0.0.0' to start it${NC}"
echo ""
echo -e "${YELLOW}No Fooocus here — this box has no GPU. Use kaggle-gpu-notebook.ipynb${NC}"
echo -e "${YELLOW}for image generation instead.${NC}"
echo -e "${YELLOW}SSL is not configured — this is HTTP only.${NC}"
echo -e "${CYAN}A Simple Corp.${NC}"
