#!/usr/bin/env bash

set -euo pipefail

#if [ $# -lt 2 ]; then
#    echo "Usage: $0 <private_key_file> <git_repo_url>"
#    exit 1
#fi

KEY_SRC="/home/ubuntu/azure-key"
REPO_URL="git@github.com:tbendall/cumulus_ansible.git"
SSH_DIR="$HOME/.ssh"
KEY_DEST="$SSH_DIR/$(basename "$KEY_SRC")"
TEMP_CLONE_DIR="$(mktemp -d)"
TARGET_DIR="/etc/ansible"
PRESERVE_DIR="scripts"

sudo chown ubuntu:ubuntu . -R

# Ensure ~/.ssh exists
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

# Move the key into place
cp "$KEY_SRC" "$KEY_DEST"
chmod 600 "$KEY_DEST"

# Start ssh-agent if needed
if ! pgrep -u "$USER" ssh-agent > /dev/null; then
    eval "$(ssh-agent -s)"
fi

KEY_DEST="$SSH_DIR/$(basename "$KEY_SRC")"
# Add the key to the agent
ssh-add "$KEY_DEST"

# Rewrite HTTPS → SSH if needed
if [[ "$REPO_URL" =~ ^https://github.com ]]; then
    REPO_URL="${REPO_URL/https:\/\/github.com/git@github.com:}"
fi

echo "Cloning repository into temporary directory: $TEMP_CLONE_DIR"
git clone "$REPO_URL" "$TEMP_CLONE_DIR"

echo "Preparing to update $TARGET_DIR while preserving $PRESERVE_DIR"

# Ensure target exists
sudo mkdir -p "$TARGET_DIR"

TARGET_DIR="/etc/ansible"
PRESERVE_DIR="scripts"

# Remove everything EXCEPT the preserved directory
sudo find "$TARGET_DIR" -mindepth 1 -maxdepth 1 ! -name "$PRESERVE_DIR" -exec rm -rf {} +

# Copy new repo contents in, but do NOT overwrite the preserved directory
sudo cp -R "$TEMP_CLONE_DIR"/. "$TARGET_DIR"

sudo chown ubuntu:ubuntu . -R


git -C "$TARGET_DIR" config user.name "Tristan Bendall"
git -C "$TARGET_DIR" config user.email "tristan@bendall.co"

# Optional: ensure Git always uses SSH for this repo
git -C "$TARGET_DIR" config core.sshCommand "ssh -i $KEY_DEST -o IdentitiesOnly=yes"

sudo apt update -y
sudo apt install netplan.io kea -y

ansible-galaxy collection install nvidia.nvue

sudo cp kea/* /etc/kea/
sudo systemctl restart kea-dhcp4-server


### Docker

echo "Installing Docker..."
sudo apt-get update -y
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo systemctl enable docker
sudo systemctl start docker

echo "Deploying gnmic via docker-compose..."
cd /etc/ansible/telemetry/gnmic
sudo docker compose down || true
sudo docker compose up -d

echo "Deploying Prometheus + Grafana via docker-compose..."
cd /etc/ansible/telemetry
sudo docker compose down || true
sudo docker compose up -d

docker network create -d macvlan \
  --subnet=192.168.200.0/24 \
  --gateway=192.168.200.1 \
  -o parent=eth0 \
  dhcp-macvlan

echo "Deploying Kea via docker-compose..."
cd /etc/ansible/kea
sudo docker compose down || true
sudo docker compose up -d

ansible-galaxy collection install nvidia.nvue

sudo cp kea/* /etc/kea/
sudo systemctl restart kea-dhcp4-server

echo "Done. /etc/ansible updated, preserving $TARGET_DIR/$PRESERVE_DIR"