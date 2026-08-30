#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR=/opt/chhabi/app
VENV_DIR=/opt/chhabi/venv
ENV_FILE=/opt/chhabi/shared/.env

cd "$APP_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Missing $ENV_FILE" >&2
    exit 1
fi

run_django() {
    sudo -u chhabi bash -c "set -a; source '$ENV_FILE'; set +a; cd '$APP_DIR'; '$VENV_DIR/bin/python' $*"
}

sudo -u chhabi "$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
sudo -u chhabi "$VENV_DIR/bin/python" -m pip install -r requirements.txt
run_django manage.py check --deploy
run_django manage.py migrate --noinput
run_django manage.py collectstatic --noinput

sudo systemctl restart chhabi
sudo systemctl reload nginx
sudo systemctl --no-pager --full status chhabi
