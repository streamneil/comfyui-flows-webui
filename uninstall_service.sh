#!/bin/bash

# ComfyUI Flows WebUI - Systemd Service Uninstallation Script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service configuration
SERVICE_NAME="comfyui-flows-webui"
SERVICE_FILE="${SERVICE_NAME}.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_FILE}"

echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}ComfyUI Flows WebUI Service Uninstaller${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this script as root${NC}"
    echo -e "${YELLOW}Run as a regular user. The script will use sudo when needed.${NC}"
    exit 1
fi

# Check if service exists
if [ ! -f "$SERVICE_PATH" ]; then
    echo -e "${YELLOW}Service is not installed${NC}"
    echo -e "Service file not found: $SERVICE_PATH"
    exit 0
fi

echo -e "${YELLOW}Found installed service:${NC}"
echo -e "  $SERVICE_PATH"
echo ""

# Check if service is running
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${YELLOW}Service is currently running${NC}"
    SERVICE_RUNNING=true
else
    echo -e "Service is not running"
    SERVICE_RUNNING=false
fi

# Check if service is enabled
if sudo systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "${YELLOW}Service is enabled (auto-start on boot)${NC}"
    SERVICE_ENABLED=true
else
    echo -e "Service is not enabled"
    SERVICE_ENABLED=false
fi

# Confirm uninstallation
echo ""
echo -e "${RED}Warning: This will completely remove the systemd service${NC}"
read -p "Continue with uninstallation? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Uninstallation cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}Uninstalling service...${NC}"

# Stop service if running
if [ "$SERVICE_RUNNING" = true ]; then
    echo -e "Stopping service..."
    sudo systemctl stop "$SERVICE_NAME"
    echo -e "${GREEN}✓ Service stopped${NC}"
fi

# Disable service if enabled
if [ "$SERVICE_ENABLED" = true ]; then
    echo -e "Disabling service..."
    sudo systemctl disable "$SERVICE_NAME"
    echo -e "${GREEN}✓ Service disabled${NC}"
fi

# Remove service file
echo -e "Removing service file..."
sudo rm -f "$SERVICE_PATH"
echo -e "${GREEN}✓ Service file removed${NC}"

# Reload systemd daemon
echo -e "Reloading systemd daemon..."
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd daemon reloaded${NC}"

# Reset failed state (if any)
sudo systemctl reset-failed "$SERVICE_NAME" 2>/dev/null || true

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Uninstallation Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "The service has been completely removed from systemd."
echo -e "You can reinstall it anytime by running:"
echo -e "  ${GREEN}./install_service.sh${NC}"
echo ""
