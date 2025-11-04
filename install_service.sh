#!/bin/bash

# ComfyUI Flows WebUI - Systemd Service Installation Script
# This script installs the service to be managed by systemctl

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
TEMPLATE_FILE="${SERVICE_NAME}.service.template"

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}ComfyUI Flows WebUI Service Installer${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this script as root${NC}"
    echo -e "${YELLOW}Run as a regular user. The script will use sudo when needed.${NC}"
    exit 1
fi

# Check if template file exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${RED}Error: Template file not found: $TEMPLATE_FILE${NC}"
    exit 1
fi

# Get current user and group
CURRENT_USER=$(whoami)
CURRENT_GROUP=$(id -gn)

echo -e "${YELLOW}Detecting configuration...${NC}"
echo -e "User: ${GREEN}$CURRENT_USER${NC}"
echo -e "Group: ${GREEN}$CURRENT_GROUP${NC}"

# Get working directory (absolute path)
WORKING_DIR=$(pwd)
echo -e "Working Directory: ${GREEN}$WORKING_DIR${NC}"

# Check if wan22_i2v_14b_4.py exists
if [ ! -f "$WORKING_DIR/wan22_i2v_14b_4.py" ]; then
    echo -e "${RED}Error: wan22_i2v_14b_4.py not found in current directory${NC}"
    echo -e "${YELLOW}Please run this script from the project root directory${NC}"
    exit 1
fi

# Detect Python
PYTHON_BIN=""
if command -v python3 &> /dev/null; then
    PYTHON_BIN=$(which python3)
elif command -v python &> /dev/null; then
    PYTHON_BIN=$(which python)
else
    echo -e "${RED}Error: Python not found${NC}"
    exit 1
fi

PYTHON_PATH=$(dirname "$PYTHON_BIN")
echo -e "Python Binary: ${GREEN}$PYTHON_BIN${NC}"
echo -e "Python Version: ${GREEN}$($PYTHON_BIN --version)${NC}"

# Check Python dependencies
echo ""
echo -e "${YELLOW}Checking Python dependencies...${NC}"
MISSING_DEPS=()

for pkg in fastapi uvicorn httpx pydantic; do
    if ! $PYTHON_BIN -c "import $pkg" 2>/dev/null; then
        MISSING_DEPS+=("$pkg")
    fi
done

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo -e "${RED}Warning: Missing Python packages: ${MISSING_DEPS[*]}${NC}"
    echo -e "${YELLOW}Install with: pip install ${MISSING_DEPS[*]}${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ All dependencies installed${NC}"
fi

# Generate service file from template
echo ""
echo -e "${YELLOW}Generating service file...${NC}"

TMP_SERVICE_FILE="/tmp/${SERVICE_FILE}"

sed -e "s|{{USER}}|$CURRENT_USER|g" \
    -e "s|{{GROUP}}|$CURRENT_GROUP|g" \
    -e "s|{{WORKING_DIR}}|$WORKING_DIR|g" \
    -e "s|{{PYTHON_BIN}}|$PYTHON_BIN|g" \
    -e "s|{{PYTHON_PATH}}|$PYTHON_PATH|g" \
    "$TEMPLATE_FILE" > "$TMP_SERVICE_FILE"

echo -e "${GREEN}✓ Service file generated${NC}"

# Show the generated service file
echo ""
echo -e "${BLUE}Generated service file:${NC}"
echo -e "${BLUE}----------------------------------------${NC}"
cat "$TMP_SERVICE_FILE"
echo -e "${BLUE}----------------------------------------${NC}"

# Confirm installation
echo ""
read -p "Install this service? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Installation cancelled${NC}"
    rm -f "$TMP_SERVICE_FILE"
    exit 0
fi

# Install service file
echo ""
echo -e "${YELLOW}Installing service...${NC}"

# Copy service file to systemd directory
sudo cp "$TMP_SERVICE_FILE" "/etc/systemd/system/${SERVICE_FILE}"
echo -e "${GREEN}✓ Service file installed to /etc/systemd/system/${SERVICE_FILE}${NC}"

# Reload systemd daemon
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd daemon reloaded${NC}"

# Clean up
rm -f "$TMP_SERVICE_FILE"

# Ask if user wants to enable the service
echo ""
read -p "Enable service to start on boot? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl enable "$SERVICE_NAME"
    echo -e "${GREEN}✓ Service enabled for auto-start${NC}"
fi

# Ask if user wants to start the service now
echo ""
read -p "Start service now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl start "$SERVICE_NAME"
    sleep 2
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}✓ Service started successfully${NC}"
    else
        echo -e "${RED}✗ Service failed to start${NC}"
        echo -e "${YELLOW}Check logs with: sudo journalctl -u $SERVICE_NAME -f${NC}"
    fi
fi

# Show usage instructions
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Service Management Commands:${NC}"
echo ""
echo -e "${GREEN}Start service:${NC}"
echo -e "  sudo systemctl start $SERVICE_NAME"
echo ""
echo -e "${GREEN}Stop service:${NC}"
echo -e "  sudo systemctl stop $SERVICE_NAME"
echo ""
echo -e "${GREEN}Restart service:${NC}"
echo -e "  sudo systemctl restart $SERVICE_NAME"
echo ""
echo -e "${GREEN}Check status:${NC}"
echo -e "  sudo systemctl status $SERVICE_NAME"
echo ""
echo -e "${GREEN}Enable auto-start:${NC}"
echo -e "  sudo systemctl enable $SERVICE_NAME"
echo ""
echo -e "${GREEN}Disable auto-start:${NC}"
echo -e "  sudo systemctl disable $SERVICE_NAME"
echo ""
echo -e "${GREEN}View logs:${NC}"
echo -e "  sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo -e "${GREEN}View recent logs:${NC}"
echo -e "  sudo journalctl -u $SERVICE_NAME -n 100"
echo ""
echo -e "${YELLOW}Service URL:${NC}"
echo -e "  http://localhost:5014"
echo -e "  http://localhost:5014/docs (API Documentation)"
echo ""
echo -e "${YELLOW}To uninstall the service, run:${NC}"
echo -e "  ./uninstall_service.sh"
echo ""
echo -e "${BLUE}========================================${NC}"
