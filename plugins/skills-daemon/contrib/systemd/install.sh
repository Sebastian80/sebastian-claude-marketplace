#!/bin/bash
# Install skills-daemon as a systemd user service
#
# Usage: ./install.sh [--enable] [--start]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/skills-daemon.service"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
DIM='\033[2m'
RESET='\033[0m'

echo -e "${DIM}Installing skills-daemon systemd service...${RESET}"

# Create user systemd directory
mkdir -p "$USER_SYSTEMD_DIR"

# Copy service file
cp "$SERVICE_FILE" "$USER_SYSTEMD_DIR/"
echo -e "${GREEN}Installed:${RESET} $USER_SYSTEMD_DIR/skills-daemon.service"

# Reload systemd
systemctl --user daemon-reload
echo -e "${GREEN}Reloaded:${RESET} systemd user daemon"

# Parse arguments
ENABLE=false
START=false
for arg in "$@"; do
    case $arg in
        --enable) ENABLE=true ;;
        --start) START=true ;;
    esac
done

if $ENABLE; then
    systemctl --user enable skills-daemon
    echo -e "${GREEN}Enabled:${RESET} skills-daemon service"
fi

if $START; then
    # Stop any existing daemon first
    if pgrep -f "skills_daemon.main" > /dev/null; then
        echo -e "${DIM}Stopping existing daemon...${RESET}"
        pkill -f "skills_daemon.main" || true
        sleep 1
    fi
    systemctl --user start skills-daemon
    echo -e "${GREEN}Started:${RESET} skills-daemon service"
fi

echo ""
echo -e "${GREEN}Installation complete!${RESET}"
echo ""
echo "Commands:"
echo "  systemctl --user status skills-daemon   # Check status"
echo "  systemctl --user start skills-daemon    # Start service"
echo "  systemctl --user stop skills-daemon     # Stop service"
echo "  systemctl --user restart skills-daemon  # Restart service"
echo "  journalctl --user -u skills-daemon -f   # View logs"
