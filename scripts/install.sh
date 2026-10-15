#!/usr/bin/env bash
# ==============================================================================
# DevDesk Local Ecosystem: Complete Suite Installer
# Repository: https://github.com/Dinu-Sreekumar/devdesk-ecosystem.git
# Usage:
#   Remote: curl -fsSL https://raw.githubusercontent.com/Dinu-Sreekumar/devdesk-ecosystem/main/scripts/install.sh | bash
#   Local:  ./scripts/install.sh
# ==============================================================================
set -e

REPO="Dinu-Sreekumar/devdesk-ecosystem"
VERSION="v0.1.0"
INSTALL_DIR="${DEV_DESK_INSTALL_DIR:-$HOME/.local/bin}"
BINARIES=("vault" "netwatch" "workpulse")

# Styling
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

echo -e "${BOLD}${BLUE}======================================================${NC}"
echo -e "${BOLD}          DevDesk Local Ecosystem Installer           ${NC}"
echo -e "  Repo: https://github.com/${REPO}                      "
echo -e "${BOLD}${BLUE}======================================================${NC}"
echo ""

# --- 1. Pre-Flight Compatibility Checks ---
echo -e "${BOLD}--> [1/4] Checking system compatibility...${NC}"

OS="$(uname -s)"
ARCH="$(uname -m)"

if [ "$OS" != "Linux" ]; then
    echo -e "${RED}❌ Incompatible OS: Pre-compiled binaries require Linux (Detected: $OS).${NC}"
    echo "   To install on other operating systems, clone the repository and build from source:"
    echo "     git clone https://github.com/${REPO}.git"
    echo "     cd devdesk-ecosystem && make build"
    exit 1
fi

if [ "$ARCH" != "x86_64" ]; then
    echo -e "${RED}❌ Incompatible Architecture: Pre-compiled binaries require x86_64 (Detected: $ARCH).${NC}"
    echo "   For ARM/aarch64 or 32-bit systems, please build from source:"
    echo "     git clone https://github.com/${REPO}.git"
    echo "     cd devdesk-ecosystem && make build"
    exit 1
fi

if command -v ldd >/dev/null 2>&1; then
    LIBC_VER="$(ldd --version 2>&1 | head -n1)"
    echo -e "    ${GREEN}✓${NC} C Library: $LIBC_VER"
fi
echo -e "    ${GREEN}✓${NC} Host platform verified: Linux (x86_64)"
echo ""

# --- 2. Prepare Target Directory ---
echo -e "${BOLD}--> [2/4] Verifying destination directory...${NC}"
mkdir -p "$INSTALL_DIR"
echo -e "    ${GREEN}✓${NC} Target path: $INSTALL_DIR"
echo ""

# --- 3. Install Binaries (Local ./dist first, then GitHub Releases) ---
echo -e "${BOLD}--> [3/4] Installing DevDesk utilities...${NC}"

BASE_URL="https://github.com/${REPO}/releases/download/${VERSION}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
LOCAL_DIST="$(cd "$SCRIPT_DIR/../dist" 2>/dev/null && pwd || echo "")"

for BIN in "${BINARIES[@]}"; do
    DEST="$INSTALL_DIR/$BIN"
    
    # Check if compiled binary exists locally in cloned repo
    if [ -n "$LOCAL_DIST" ] && [ -f "$LOCAL_DIST/$BIN" ]; then
        echo -e "    ${BLUE}●${NC} Installing $BIN from local workspace (dist/$BIN)..."
        cp "$LOCAL_DIST/$BIN" "$DEST"
        chmod +x "$DEST"
        echo -e "      ${GREEN}✓ Installed $BIN to $DEST${NC}"
        continue
    fi

    # Remote download from GitHub Release
    echo -e "    ${BLUE}●${NC} Downloading $BIN ($VERSION) from GitHub Releases..."
    DOWNLOAD_SUCCESS=false

    if command -v curl >/dev/null 2>&1; then
        if curl -fL --progress-bar "$BASE_URL/$BIN" -o "$DEST" 2>/dev/null; then
            DOWNLOAD_SUCCESS=true
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q --show-progress "$BASE_URL/$BIN" -O "$DEST" 2>/dev/null; then
            DOWNLOAD_SUCCESS=true
        fi
    else
        echo -e "${RED}❌ Error: Neither 'curl' nor 'wget' was found on your system.${NC}"
        echo "   Please install curl or wget, or clone the repo directly."
        exit 1
    fi

    if [ "$DOWNLOAD_SUCCESS" = true ] && [ -s "$DEST" ]; then
        chmod +x "$DEST"
        echo -e "      ${GREEN}✓ Installed $BIN to $DEST${NC}"
    else
        # Remove potential empty file created by failed curl
        rm -f "$DEST"
        echo -e "${RED}❌ Error: Failed to download '$BIN' from ${BASE_URL}/${BIN}${NC}"
        echo ""
        echo -e "${YELLOW}Note: The GitHub Release '$VERSION' might not be published yet or the repo is empty.${NC}"
        echo -e "You can clone and build the ecosystem locally using:"
        echo ""
        echo "  git clone https://github.com/${REPO}.git"
        echo "  cd devdesk-ecosystem"
        echo "  make setup && make build"
        echo "  ./scripts/install.sh"
        echo ""
        exit 1
    fi

    # Post-install verification smoke test
    if ! "$DEST" --help >/dev/null 2>&1; then
        echo -e "      ${RED}❌ Execution check failed for $BIN.${NC}"
        echo -e "      ${YELLOW}Your system's C library (glibc/musl) appears incompatible with this pre-compiled binary.${NC}"
        echo "      To build natively from source for your exact system:"
        echo "        git clone https://github.com/${REPO}.git"
        echo "        cd devdesk-ecosystem"
        echo "        make setup && make build && make install"
        exit 1
    fi
done

echo ""
echo -e "${BOLD}${GREEN}======================================================${NC}"
echo -e "${BOLD}${GREEN}✓ All 3 DevDesk utilities successfully installed!     ${NC}"
echo -e "${BOLD}${GREEN}======================================================${NC}"
echo ""

# --- 4. Environment Verification & PATH Check ---
echo -e "${BOLD}--> [4/4] Environment check...${NC}"
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo -e "${YELLOW}⚠️  Warning: $INSTALL_DIR is not currently in your \$PATH.${NC}"
    echo "   To run 'vault', 'netwatch', and 'workpulse' from anywhere, append this to your shell profile:"
    echo ""
    echo -e "   ${BOLD}For Bash (~/.bashrc):${NC}"
    echo "     echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
    echo ""
    echo -e "   ${BOLD}For Zsh (~/.zshrc):${NC}"
    echo "     echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
    echo ""
else
    echo -e "    ${GREEN}✓${NC} $INSTALL_DIR is present in your \$PATH."
fi

echo -e "${BOLD}Quick Verification Commands:${NC}"
echo "  vault --help"
echo "  netwatch --help"
echo "  workpulse --help"
echo ""