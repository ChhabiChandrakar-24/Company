#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/chhabi/app
VENV_DIR=/opt/chhabi/venv
ENV_FILE=/opt/chhabi/shared/.env

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: sudo bash deploy/aws/deploy-release.sh"
  exit 1
fi
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}; copy deploy/aws/chhabi.env.example and fill it first."
  exit 1
fi

chown -R chhabi:www-data "${APP_DIR}" "${VENV_DIR}"
sudo -u chhabi "${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a
sudo -u chhabi --preserve-env "${VENV_DIR}/bin/python" "${APP_DIR}/manage.py" check --deploy
sudo -u chhabi --preserve-env "${VENV_DIR}/bin/python" "${APP_DIR}/manage.py" migrate --noinput
sudo -u chhabi --preserve-env "${VENV_DIR}/bin/python" "${APP_DIR}/manage.py" collectstatic --noinput

nginx -t
systemctl enable --now nginx chhabi
systemctl restart chhabi
systemctl --no-pager --full status chhabi
