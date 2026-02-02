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



echo "Done. /etc/ansible updated, preserving $TARGET_DIR/$PRESERVE_DIR"