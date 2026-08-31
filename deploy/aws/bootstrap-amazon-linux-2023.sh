#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run with: sudo bash deploy/aws/bootstrap-amazon-linux-2023.sh" >&2
    exit 1
fi

source /etc/os-release
if [[ "${ID:-}" != "amzn" || "${VERSION_ID:-}" != "2023" ]]; then
    echo "This bootstrap supports Amazon Linux 2023 only." >&2
    exit 1
fi

dnf update -y
dnf install -y \
    git nginx rsync tar gzip \
    python3.11 python3.11-devel \
    gcc gcc-c++ make redhat-rpm-config pkgconf-pkg-config \
    mariadb105 mariadb105-server mariadb105-devel \
    libjpeg-turbo-devel zlib-devel libffi-devel openssl-devel \
    freetype-devel lcms2-devel openjpeg2-devel libtiff-devel \
    libxml2-devel libxslt-devel cairo-devel pango-devel \
    certbot python3-certbot-nginx

getent group chhabi >/dev/null || groupadd --system chhabi
id -u chhabi >/dev/null 2>&1 || useradd --system --gid chhabi \
    --home-dir /opt/chhabi --create-home --shell /sbin/nologin chhabi

install -d -m 755 -o chhabi -g chhabi \
    /opt/chhabi/app /opt/chhabi/shared \
    /opt/chhabi/shared/media /opt/chhabi/shared/staticfiles
chmod 755 /opt/chhabi

if [[ ! -x /opt/chhabi/venv/bin/python ]]; then
    sudo -u chhabi python3.11 -m venv /opt/chhabi/venv
fi

systemctl enable nginx
systemctl enable --now mariadb
echo "Base setup complete. Continue at deploy/aws/README.md step 5."
