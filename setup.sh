#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

PROJECT_DIR=$(pwd)
VENV_DIR="$PROJECT_DIR/venv"
CLONE_DIR="$PROJECT_DIR/.tmp_waveshare"

# Error handling function to catch unexpected failures
error_handler() {
    echo "❌ ERROR: Installation failed during the setup phase."
    echo "⚠️ The systemd service was NOT created or modified to avoid breaking system states."
    echo "🧹 Cleaning up temporary files..."
    rm -rf "$CLONE_DIR"
    exit 1
}

# Trap any error signal (non-zero exit codes) and run the error handler
trap 'error_handler' ERR

echo "🚀 Initializing InkNode standalone deployment..."

# Ensure core system dependencies are present
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip network-manager fonts-dejavu git

# Purge any stale installation artifacts
rm -rf "$CLONE_DIR"
rm -rf "$PROJECT_DIR/waveshare_epd"

echo "📦 Fetching driver library using Git Sparse-Checkout (Saving space)..."
mkdir -p "$CLONE_DIR"
cd "$CLONE_DIR"
git init
git remote add origin https://github.com/waveshareteam/e-Paper.git
git config core.sparseCheckout true

# Tell Git to ONLY download the specific Python folders we need
echo "RaspberryPi_JetsonNano/python/lib/waveshare_epd/" >> .git/info/sparse-checkout
echo "RaspberryPi_JetsonNano/python/pic/Font.ttc" >> .git/info/sparse-checkout

# Pull only the requested files, without history
git pull --depth 1 origin master

# Navigate back to the project root
cd "$PROJECT_DIR"

echo "📂 Injecting hardware package into project root..."
cp -r "$CLONE_DIR/RaspberryPi_JetsonNano/python/lib/waveshare_epd" "$PROJECT_DIR/"
mkdir -p "$PROJECT_DIR/pic"
cp "$CLONE_DIR/RaspberryPi_JetsonNano/python/pic/Font.ttc" "$PROJECT_DIR/pic/"

echo "🧹 Clearing temporary git clones..."
rm -rf "$CLONE_DIR"

echo "🐍 Setting up Python environment..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

# -------------------------------------------------------------------------
# ALL PREREQUISITES SUCCESSFUL - PROCEED TO SERVICE CREATION
# -------------------------------------------------------------------------
# trap - ERR

# echo "⚙️ Provisioning Systemd service engine..."
# sudo bash -c "cat > /etc/systemd/system/epaper-dash.service << EOF
# [Unit]
# Description=InkNode E-Paper Dashboard Service
# After=network.target

# [Service]
# Type=simple
# User=root
# WorkingDirectory=$PROJECT_DIR
# ExecStart=$VENV_DIR/bin/python $PROJECT_DIR/boot_manager.py
# Restart=on-failure
# RestartSec=10

# [Install]
# WantedBy=multi-user.target
# EOF"

# echo "🔄 Activating system daemon..."
# sudo systemctl daemon-reload
# sudo systemctl enable epaper-dash.service
# sudo systemctl restart epaper-dash.service

sudo chown -R $USER $PROJECT_DIR
echo "✅ Deployment finished successfully. System is active."
