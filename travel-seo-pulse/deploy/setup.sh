#!/usr/bin/env bash
# Deploy travel-seo-pulse to a fresh Debian/Ubuntu VPS.
# Idempotent - safe to re-run.
#
# Prereqs on local machine:
#   - SSH access as root to the target VPS
#   - This deploy/ directory present on local machine
#
# Usage:
#   scp -r deploy/ root@<vps>:/root/
#   ssh root@<vps> "bash /root/deploy/setup.sh"
#   # Then create /etc/travel-seo-pulse.env with secrets (see env.example)

set -euo pipefail

REPO_URL="https://github.com/jessejameswoods/jessejameswoods.com.git"
APP_DIR="/opt/travel-seo-pulse"
VENV_DIR="${APP_DIR}/.venv"
USER_NAME="pulse"
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== [1/7] System packages ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  python3 python3-venv python3-pip \
  git curl ca-certificates tzdata

echo "=== [2/7] User + directories ==="
id -u ${USER_NAME} >/dev/null 2>&1 || useradd -r -m -d /home/${USER_NAME} -s /bin/bash ${USER_NAME}
mkdir -p ${APP_DIR}
chown ${USER_NAME}:${USER_NAME} ${APP_DIR}
mkdir -p /var/log/travel-seo-pulse
chown ${USER_NAME}:${USER_NAME} /var/log/travel-seo-pulse

echo "=== [3/7] Clone / update repo ==="
if [ -d "${APP_DIR}/.git" ]; then
  sudo -u ${USER_NAME} git -C ${APP_DIR} fetch --depth 1 origin main
  sudo -u ${USER_NAME} git -C ${APP_DIR} reset --hard origin/main
else
  sudo -u ${USER_NAME} git clone --depth 1 ${REPO_URL} ${APP_DIR}
fi

echo "=== [4/7] Python venv + deps ==="
sudo -u ${USER_NAME} python3 -m venv ${VENV_DIR}
sudo -u ${USER_NAME} ${VENV_DIR}/bin/pip install --quiet --upgrade pip wheel
sudo -u ${USER_NAME} ${VENV_DIR}/bin/pip install --quiet -r ${APP_DIR}/travel-seo-pulse/requirements.txt

echo "=== [5/7] Runner wrapper ==="
install -m 0755 ${DEPLOY_DIR}/travel-seo-pulse-run.sh /usr/local/bin/travel-seo-pulse-run

echo "=== [6/7] systemd unit + timer ==="
install -m 0644 ${DEPLOY_DIR}/travel-seo-pulse.service /etc/systemd/system/travel-seo-pulse.service
install -m 0644 ${DEPLOY_DIR}/travel-seo-pulse.timer /etc/systemd/system/travel-seo-pulse.timer
systemctl daemon-reload
systemctl enable --now travel-seo-pulse.timer

echo "=== [7/7] Done ==="
echo "Next: create /etc/travel-seo-pulse.env with these keys (see env.example):"
echo "  ANTHROPIC_API_KEY, SUBSTACK_USER_ID, SUBSTACK_COOKIE, HEALTHCHECK_URL"
echo ""
echo "Verify:"
echo "  systemctl list-timers travel-seo-pulse.timer"
echo "  systemctl start travel-seo-pulse.service   # manual test run"
echo "  journalctl -u travel-seo-pulse.service -f"
