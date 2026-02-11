#!/usr/bin/env bash
set -e

echo "=== Prometheus Installer ==="

# Variables
PROM_USER="prometheus"
PROM_DIR="/etc/prometheus"
PROM_DATA="/var/lib/prometheus"
SERVICE_FILE="/etc/systemd/system/prometheus.service"
PROM_URL=$(curl -s https://api.github.com/repos/prometheus/prometheus/releases/latest \
  | grep browser_download_url \
  | grep linux-amd64.tar.gz \
  | cut -d '"' -f 4)

echo "Using Prometheus release: $PROM_URL"

# Create user if missing
if ! id "$PROM_USER" >/dev/null 2>&1; then
  echo "Creating prometheus user..."
  sudo useradd --no-create-home --shell /bin/false $PROM_USER
fi

# Create directories
echo "Creating directories..."
sudo mkdir -p $PROM_DIR
sudo mkdir -p $PROM_DATA

# Download Prometheus
echo "Downloading Prometheus..."
cd /tmp
curl -LO "$PROM_URL"
TAR_FILE=$(basename "$PROM_URL")
DIR_NAME="${TAR_FILE%.tar.gz}"

echo "Extracting..."
tar -xvf "$TAR_FILE"

# Install binaries
echo "Installing binaries..."
sudo cp "$DIR_NAME/prometheus" /usr/local/bin/
sudo cp "$DIR_NAME/promtool" /usr/local/bin/

# Install consoles
echo "Skipping console templates (Prometheus 3.x no longer includes them)"

# Prometheus config
echo "Writing Prometheus config..."
sudo tee $PROM_DIR/prometheus.yml >/dev/null <<EOF
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: "gnmic"
    static_configs:
      - targets: ["localhost:9804"]
EOF

# Permissions
echo "Setting permissions..."
sudo chown -R $PROM_USER:$PROM_USER $PROM_DIR
sudo chown -R $PROM_USER:$PROM_USER $PROM_DATA

# Systemd service
echo "Creating systemd service..."
sudo tee $SERVICE_FILE >/dev/null <<EOF
[Unit]
Description=Prometheus Monitoring
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus \\
  --config.file=/etc/prometheus/prometheus.yml \\
  --storage.tsdb.path=/var/lib/prometheus \\
  --web.console.templates=/etc/prometheus/consoles \\
  --web.console.libraries=/etc/prometheus/console_libraries

[Install]
WantedBy=multi-user.target
EOF

# Reload + start
echo "Reloading systemd..."
sudo systemctl daemon-reload

echo "Enabling Prometheus..."
sudo systemctl enable prometheus

echo "Starting Prometheus..."
sudo systemctl restart prometheus

echo "Checking status..."
sudo systemctl --no-pager status prometheus

echo "=== Prometheus installation complete ==="
echo "Visit: http://$(hostname -I | awk '{print $1}'):9090"

