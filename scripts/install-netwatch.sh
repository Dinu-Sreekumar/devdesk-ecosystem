#!/usr/bin/env bash
# ==============================================================================
# NetWatch Standalone Installer
# Repository: https://github.com/Dinu-Sreekumar/devdesk-ecosystem.git
# Usage:
#   Remote: curl -fsSL https://raw.githubusercontent.com/Dinu-Sreekumar/devdesk-ecosystem/main/scripts/install-netwatch.sh | bash
#   Local:  ./scripts/install-netwatch.sh
# ==============================================================================
set -e

REPO="Dinu-Sreekumar/devdesk-ecosystem"
VERSION="v0.1.0"
INSTALL_DIR="${DEV_DESK_INSTALL_DIR:-$HOME/.local/bin}"
BIN="netwatch"

# Styling
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m"

echo -e "${BOLD}${BLUE}======================================================${NC}"
echo -e "${BOLD}            NetWatch Standalone Installer             ${NC}"
echo -e "  Repo: https://github.com/${REPO}                      "
echo -e "${BOLD}${BLUE}======================================================${NC}"
echo ""

# --- 1. Compatibility Check ---
echo -e "${BOLD}--> [1/3] Checking system compatibility...${NC}"
if [ "$(uname -s)" != "Linux" ] || [ "$(uname -m)" != "x86_64" ]; then
    echo -e "${RED}❌ Incompatible Host: Pre-compiled binary requires Linux x86_64.${NC}"
    echo "   Detected: $(uname -s) ($(uname -m))"
    echo "   To install on other architectures, build from source:"
    echo "     git clone https://github.com/${REPO}.git"
    echo "     cd devdesk-ecosystem && make build-netwatch"
    exit 1
fi
echo -e "    ${GREEN}✓${NC} Linux x86_64 verified."
echo ""

# --- 2. Installation (Local ./dist first, then GitHub Releases) ---
echo -e "${BOLD}--> [2/3] Installing $BIN...${NC}"
mkdir -p "$INSTALL_DIR"
DEST="$INSTALL_DIR/$BIN"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
LOCAL_DIST="$(cd "$SCRIPT_DIR/../dist" 2>/dev/null && pwd || echo "")"

if [ -n "$LOCAL_DIST" ] && [ -f "$LOCAL_DIST/$BIN" ]; then
    echo -e "    ${BLUE}●${NC} Found local build in dist/$BIN. Copying..."
    cp "$LOCAL_DIST/$BIN" "$DEST"
    chmod +x "$DEST"
    echo -e "      ${GREEN}✓ Successfully installed $BIN to $DEST${NC}"
else
    URL="https://github.com/${REPO}/releases/download/${VERSION}/${BIN}"
    echo -e "    ${BLUE}●${NC} Downloading from $URL..."
    DOWNLOAD_SUCCESS=false

    if command -v curl >/dev/null 2>&1; then
        if curl -fL --progress-bar "$URL" -o "$DEST" 2>/dev/null; then
            DOWNLOAD_SUCCESS=true
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q --show-progress "$URL" -O "$DEST" 2>/dev/null; then
            DOWNLOAD_SUCCESS=true
        fi
    else
        echo -e "${RED}❌ Error: Neither curl nor wget is available.${NC}"
        exit 1
    fi

    if [ "$DOWNLOAD_SUCCESS" = true ] && [ -s "$DEST" ]; then
        chmod +x "$DEST"
        echo -e "      ${GREEN}✓ Successfully installed $BIN to $DEST${NC}"
    else
        rm -f "$DEST"
        echo -e "${RED}❌ Error: Could not download $BIN from $URL${NC}"
        echo ""
        echo -e "${YELLOW}Note: The GitHub Release '$VERSION' might not be published yet.${NC}"
        echo "You can clone and build from source:"
        echo "  git clone https://github.com/${REPO}.git"
        echo "  cd devdesk-ecosystem && make build-netwatch"
        echo "  cp dist/netwatch ~/.local/bin/"
        exit 1
    fi
fi
echo ""

# --- 3. PATH Verification ---
echo -e "${BOLD}--> [3/3] Checking environment...${NC}"
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo -e "${YELLOW}⚠️  Note: $INSTALL_DIR is not in your \$PATH.${NC}"
    echo "   Add it with: export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo -e "${BOLD}${GREEN}✓ NetWatch is ready!${NC}"
echo "Run 'netwatch --help' to get started."
echo ""
