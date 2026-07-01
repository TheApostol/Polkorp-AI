#!/usr/bin/env bash
#
# POLKORP AI — Full production VPS deployment
# Target: Ubuntu 22.04, NVIDIA GPU (A4000 16GB / RTX 3060 12GB or similar)
#
# Installs Docker, NVIDIA Container Toolkit, brings up the full stack via
# docker-compose.yml, configures the firewall, and pulls the base models.
#
# Run as root or via sudo: sudo bash deploy-vps-full.sh

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
echo "║        POLKORP AI — VPS Deployment        ║"
echo "║        Opening the world of AI for you.   ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ---------------------------------------------------------------------------
# 0. Root check + OS check
# ---------------------------------------------------------------------------
if [[ "${EUID}" -ne 0 ]]; then
  fatal "Run this as root: sudo bash deploy-vps-full.sh"
fi
if ! grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
  warn "This script targets Ubuntu 22.04 — proceeding anyway, but expect surprises on other distros."
fi

# ---------------------------------------------------------------------------
# 1. GPU sanity check (warn, don't hard-fail — deploy can still proceed for
#    non-GPU services, but ollama/lama/fooocus need it to be useful)
# ---------------------------------------------------------------------------
if ! command -v nvidia-smi >/dev/null 2>&1; then
  warn "nvidia-smi not found. Install NVIDIA drivers first (this script installs the *container* toolkit, not the host driver)."
else
  ok "NVIDIA driver detected:"
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
fi

# ---------------------------------------------------------------------------
# 2. System update + base packages
# ---------------------------------------------------------------------------
info "Updating apt and installing base packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y curl wget git nginx python3-pip ufw fail2ban ca-certificates gnupg
ok "Base packages installed"

# ---------------------------------------------------------------------------
# 3. Docker + Docker Compose plugin
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
# 4. NVIDIA Container Toolkit
# ---------------------------------------------------------------------------
if docker info 2>/dev/null | grep -qi "nvidia"; then
  ok "NVIDIA Container Toolkit already configured"
else
  info "Installing NVIDIA Container Toolkit..."
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    | tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null
  apt-get update -y
  apt-get install -y nvidia-container-toolkit
  nvidia-ctk runtime configure --runtime=docker
  systemctl restart docker
  ok "NVIDIA Container Toolkit installed and Docker restarted"
fi

# ---------------------------------------------------------------------------
# 5. /opt/polkorp scaffold + docker-compose.yml
# ---------------------------------------------------------------------------
info "Creating ${POLKORP_DIR}..."
mkdir -p "${POLKORP_DIR}"/{dashboard,backend,volumes/ollama,volumes/fooocus-outputs}

if [[ -f "$(dirname "$0")/docker-compose.yml" ]]; then
  cp "$(dirname "$0")/docker-compose.yml" "${POLKORP_DIR}/docker-compose.yml"
  ok "Copied docker-compose.yml from installer directory"
else
  fatal "docker-compose.yml not found next to this script. Copy it into $(dirname "$0") and re-run."
fi

if [[ -f "$(dirname "$0")/dashboard.html" ]]; then
  cp "$(dirname "$0")/dashboard.html" "${POLKORP_DIR}/dashboard/index.html"
  ok "Copied dashboard.html into ${POLKORP_DIR}/dashboard/index.html"
else
  warn "dashboard.html not found next to this script — the dashboard container will have nothing to serve until you copy it in."
fi

# ---------------------------------------------------------------------------
# 6. Firewall
# ---------------------------------------------------------------------------
info "Configuring UFW..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 5050/tcp
ufw --force enable
ok "UFW enabled: 22, 80, 443, 5050 open"

# ---------------------------------------------------------------------------
# 7. Bring the stack up
# ---------------------------------------------------------------------------
info "Starting containers via docker compose..."
(cd "${POLKORP_DIR}" && docker compose up -d)
ok "Stack is up"

# ---------------------------------------------------------------------------
# 8. Pull models
#
# NOTE: the original spec listed "mistral-large" — that's Mistral's
# API-only flagship model; there are no local weights for Ollama to pull.
# Substituting "mistral" (the real Ollama tag) so this step doesn't fail.
# ---------------------------------------------------------------------------
info "Pulling AI models into Ollama (this takes a while, ~30-60GB total)..."
MODELS=(deepseek-coder-v2 llama3.1:8b mistral codeqwen)
for m in "${MODELS[@]}"; do
  info "Pulling ${m}..."
  if docker compose -f "${POLKORP_DIR}/docker-compose.yml" exec -T ollama ollama pull "${m}"; then
    ok "${m} pulled"
  else
    warn "${m} failed to pull — check 'docker compose logs ollama' and retry manually later."
  fi
done

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
PUBLIC_IP=$(curl -fsSL ifconfig.me 2>/dev/null || echo "<your-server-ip>")
echo ""
echo -e "${GREEN}${BOLD}POLKORP AI deployment complete.${NC}"
echo -e "  Dashboard:  ${CYAN}http://${PUBLIC_IP}/${NC}"
echo -e "  Backend:    ${CYAN}http://${PUBLIC_IP}:5050/${NC}"
echo -e "  Ollama:     ${CYAN}http://${PUBLIC_IP}:11434/${NC}"
echo -e "  Lama:       ${CYAN}http://${PUBLIC_IP}:8080/${NC}"
echo -e "  Fooocus:    ${CYAN}http://${PUBLIC_IP}:7865/${NC}"
echo ""
echo -e "${YELLOW}SSL is not configured yet — this is HTTP only. Put nginx behind${NC}"
echo -e "${YELLOW}certbot/Let's Encrypt once you point polkorp.com's DNS at this server.${NC}"
echo -e "${CYAN}A Simple Corp.${NC}"
