#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: sudo bash deploy/aws/bootstrap-ubuntu.sh"
  exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3 python3-venv python3-dev build-essential libpq-dev \
  libjpeg-dev zlib1g-dev libffi-dev libssl-dev wkhtmltopdf \
  nginx certbot python3-certbot-nginx git curl

id -u chhabi >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash chhabi
install -d -o chhabi -g www-data -m 0750 /opt/chhabi/app /opt/chhabi/shared
python3 -m venv /opt/chhabi/venv
/opt/chhabi/venv/bin/pip install --upgrade pip wheel setuptools

cp "${SCRIPT_DIR}/chhabi.service" /etc/systemd/system/chhabi.service
cp "${SCRIPT_DIR}/nginx.conf" /etc/nginx/sites-available/chhabi
ln -sfn /etc/nginx/sites-available/chhabi /etc/nginx/sites-enabled/chhabi
rm -f /etc/nginx/sites-enabled/default
systemctl daemon-reload

echo "Bootstrap complete. Next: create /opt/chhabi/shared/.env, then run deploy-release.sh."
