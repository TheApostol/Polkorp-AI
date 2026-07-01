#!/usr/bin/env bash
#
# POLKORP AI — Lightweight macOS installer
# Target: MacBook Air 2013, 4 GB RAM, Intel i5, macOS Monterey, ~14 GB free
#
# Installs Ollama + Lama Cleaner locally, no Docker, minimal footprint.
# Safe to re-run — every step checks before it acts.

set -euo pipefail

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
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

POLKORP_HOME="${HOME}/polkorp-ai"
TOOLS_DIR="${POLKORP_HOME}/tools"
MIN_FREE_GB=5

echo -e "${BOLD}${CYAN}"
echo "╔══════════════════════════════════════════╗"
echo "║           POLKORP AI — Mac Setup          ║"
echo "║        Opening the world of AI for you.   ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ---------------------------------------------------------------------------
# 1. Platform sanity check
# ---------------------------------------------------------------------------
if [[ "$(uname -s)" != "Darwin" ]]; then
  fatal "This installer is for macOS only. Detected: $(uname -s)"
fi
info "macOS detected: $(sw_vers -productVersion 2>/dev/null || echo unknown)"

# ---------------------------------------------------------------------------
# 2. Disk space check (minimum 5 GB free)
# ---------------------------------------------------------------------------
info "Checking free disk space..."
FREE_KB=$(df -k "${HOME}" | tail -1 | awk '{print $4}')
FREE_GB=$(( FREE_KB / 1024 / 1024 ))
if (( FREE_GB < MIN_FREE_GB )); then
  fatal "Only ${FREE_GB} GB free. POLKORP AI needs at least ${MIN_FREE_GB} GB. Free up space and re-run."
fi
ok "Disk space OK: ${FREE_GB} GB free"

# ---------------------------------------------------------------------------
# 3. Folder structure
# ---------------------------------------------------------------------------
info "Creating ${TOOLS_DIR}..."
mkdir -p "${TOOLS_DIR}"
mkdir -p "${POLKORP_HOME}/outputs"
mkdir -p "${POLKORP_HOME}/logs"
ok "Folder structure ready at ${POLKORP_HOME}"

# ---------------------------------------------------------------------------
# 4. Python 3 check
# ---------------------------------------------------------------------------
info "Checking for Python 3..."
if ! command -v python3 >/dev/null 2>&1; then
  fatal "python3 not found. Install it from https://www.python.org/downloads/ or 'brew install python3', then re-run."
fi
PY_VERSION=$(python3 --version 2>&1)
ok "Found: ${PY_VERSION}"

# ---------------------------------------------------------------------------
# 5. pipx (avoids the "externally-managed-environment" pip error on
#    Monterey+ system Pythons and Homebrew Pythons alike)
# ---------------------------------------------------------------------------
info "Checking for pipx..."
if command -v pipx >/dev/null 2>&1; then
  ok "pipx already installed"
else
  if command -v brew >/dev/null 2>&1; then
    info "Installing pipx via Homebrew..."
    brew install pipx || fatal "Homebrew pipx install failed."
  else
    warn "Homebrew not found — installing pipx via pip --user instead."
    if ! python3 -m pip install --user pipx; then
      warn "Falling back to --break-system-packages (externally-managed-environment workaround)."
      python3 -m pip install --user --break-system-packages pipx \
        || fatal "pipx install failed. Install Homebrew (https://brew.sh) and re-run for a cleaner path."
    fi
  fi
  python3 -m pipx ensurepath || true
  ok "pipx installed"
fi

# make sure pipx-installed binaries are visible in this script's PATH too
export PATH="${HOME}/.local/bin:${PATH}"

# ---------------------------------------------------------------------------
# 6. Lama Cleaner via pipx
# ---------------------------------------------------------------------------
info "Checking for Lama Cleaner..."
if command -v lama-cleaner >/dev/null 2>&1; then
  ok "Lama Cleaner already installed"
else
  info "Installing Lama Cleaner via pipx (this can take a few minutes on 4GB RAM)..."
  pipx install lama-cleaner || fatal "Lama Cleaner install failed. Check your internet connection and re-run."
  ok "Lama Cleaner installed"
fi

# ---------------------------------------------------------------------------
# 7. Ollama (official installer script)
# ---------------------------------------------------------------------------
info "Checking for Ollama..."
if command -v ollama >/dev/null 2>&1; then
  ok "Ollama already installed"
else
  info "Installing Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh || fatal "Ollama install failed. See https://ollama.com/download for manual install."
  ok "Ollama installed"
fi

# ---------------------------------------------------------------------------
# 8. Launcher script
# ---------------------------------------------------------------------------
info "Writing launcher to ${POLKORP_HOME}/start.sh..."
cat > "${POLKORP_HOME}/start.sh" << 'LAUNCHER'
#!/usr/bin/env bash
# POLKORP AI — local launcher menu
set -uo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

POLKORP_HOME="${HOME}/polkorp-ai"
export PATH="${HOME}/.local/bin:${PATH}"

pull_models() {
  echo -e "${CYAN}Pulling models (this may take a while on first run)...${NC}"
  ollama pull llama3.1:8b
  echo -e "${GREEN}Done. Run 'ollama list' to see installed models.${NC}"
}

status() {
  echo -e "${CYAN}--- POLKORP AI status ---${NC}"
  if command -v ollama >/dev/null 2>&1; then
    echo -e "${GREEN}[✓]${NC} Ollama installed"
    ollama list 2>/dev/null || echo "  (no models pulled yet — use option 4)"
  else
    echo -e "${RED}[✗]${NC} Ollama not found"
  fi
  if command -v lama-cleaner >/dev/null 2>&1; then
    echo -e "${GREEN}[✓]${NC} Lama Cleaner installed"
  else
    echo -e "${RED}[✗]${NC} Lama Cleaner not found"
  fi
  echo "Home: ${POLKORP_HOME}"
}

while true; do
  echo ""
  echo -e "${CYAN}POLKORP AI — Local Launcher${NC}"
  echo "  [1] Terminal Chat"
  echo "  [2] Lama Cleaner"
  echo "  [3] Dashboard"
  echo "  [4] Pull Models"
  echo "  [5] Status"
  echo "  [0] Exit"
  read -rp "Select: " choice
  case "$choice" in
    1) ollama run llama3.1:8b ;;
    2) echo -e "${YELLOW}Starting Lama Cleaner on http://localhost:8080 ...${NC}"; lama-cleaner --port 8080 ;;
    3)
      DASH="${POLKORP_HOME}/dashboard.html"
      if [[ -f "$DASH" ]]; then
        open "$DASH"
      else
        echo -e "${RED}dashboard.html not found in ${POLKORP_HOME}. Copy it there first.${NC}"
      fi
      ;;
    4) pull_models ;;
    5) status ;;
    0) echo "Bye."; exit 0 ;;
    *) echo -e "${YELLOW}Invalid option.${NC}" ;;
  esac
done
LAUNCHER
chmod +x "${POLKORP_HOME}/start.sh"
ok "Launcher ready: ${POLKORP_HOME}/start.sh"

echo ""
echo -e "${GREEN}${BOLD}POLKORP AI local setup complete.${NC}"
echo -e "Run: ${CYAN}${POLKORP_HOME}/start.sh${NC}"
echo -e "${YELLOW}A Simple Corp.${NC}"
