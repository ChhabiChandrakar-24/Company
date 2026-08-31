# Chhabi deployment on Amazon Linux 2023

Complete target: **Amazon Linux 2023 x86_64 EC2 + internal MariaDB + Nginx +
Gunicorn/systemd + Elastic IP + HTTPS**. RDS is not used.

## 1. Create AWS resources

1. Launch the latest Amazon Linux 2023 `x86_64` AMI. Start with `t3.medium`
   and a 30 GiB encrypted gp3 EBS volume.
2. EC2 inbound rules: SSH/22 from your IP only; HTTP/80 and HTTPS/443 from
   anywhere. Never expose port 8000. Associate an Elastic IP.
3. Do not open port 3306 in the EC2 security group. MariaDB is accessible only
   internally through `127.0.0.1`.
4. Point the domain's `A` record to the Elastic IP.

## 2. Connect and verify AL2023

```bash
ssh -i YOUR_KEY.pem ec2-user@YOUR_ELASTIC_IP
cat /etc/os-release
uname -m
```

Expected: Amazon Linux 2023 and `x86_64`. AL2023 uses DNF. We explicitly use
Python 3.11; never change the system `/usr/bin/python3` symlink (Python 3.9).

## 3. Install packages

```bash
sudo dnf update -y
sudo dnf install -y \
  git nginx rsync tar gzip \
  python3.11 python3.11-devel \
  gcc gcc-c++ make redhat-rpm-config pkgconf-pkg-config \
  mariadb105 mariadb105-server mariadb105-devel \
  libjpeg-turbo-devel zlib-devel libffi-devel openssl-devel \
  freetype-devel lcms2-devel openjpeg2-devel libtiff-devel \
  libxml2-devel libxslt-devel cairo-devel pango-devel \
  certbot python3-certbot-nginx

python3.11 --version
nginx -v
certbot --version
```

Or, after uploading this repository, run the idempotent bootstrap:

```bash
sudo bash deploy/aws/bootstrap-amazon-linux-2023.sh
```

If Certbot is unavailable because the AMI is pinned to an old repository:

```bash
sudo dnf install -y 'dnf-command(check-release-update)'
sudo dnf check-release-update
sudo dnf upgrade -y
sudo reboot
```

Reconnect and rerun package installation.

## 4. Create user, directories, and virtual environment

```bash
sudo groupadd --system chhabi
sudo useradd --system --gid chhabi --home-dir /opt/chhabi \
  --create-home --shell /sbin/nologin chhabi

sudo install -d -m 755 -o chhabi -g chhabi \
  /opt/chhabi/app /opt/chhabi/shared \
  /opt/chhabi/shared/media /opt/chhabi/shared/staticfiles
sudo chmod 755 /opt/chhabi

sudo -u chhabi python3.11 -m venv /opt/chhabi/venv
```

If the group/user already exists, skip its creation commands.

## 5. Upload code

```bash
sudo -u chhabi git clone YOUR_PRIVATE_REPOSITORY_URL /opt/chhabi/app
```

For an existing checkout:

```bash
sudo -u chhabi git -C /opt/chhabi/app pull --ff-only
```

Never upload `.venv`, `.env`, browser caches/profiles, logs, or a local DB.

## 6. Create production environment

```bash
sudo cp /opt/chhabi/app/deploy/aws/env.production.example /opt/chhabi/shared/.env
sudo chown chhabi:chhabi /opt/chhabi/shared/.env
sudo chmod 600 /opt/chhabi/shared/.env
sudo vi /opt/chhabi/shared/.env
```

Generate two independent secrets:

```bash
python3.11 -c 'import secrets; print(secrets.token_urlsafe(64))'
python3.11 -c 'import secrets; print(secrets.token_urlsafe(48))'
```
Required values:

```dotenv
DEBUG=False
SECRET_KEY=FIRST_RANDOM_VALUE
DB_INIT_PASSWORD=SECOND_RANDOM_VALUE
ALLOWED_HOSTS=hr.example.com
CSRF_TRUSTED_ORIGINS=https://hr.example.com
TIME_ZONE=Asia/Kolkata
DATABASE_URL=mysql://chhabi_app:URL_ENCODED_PASSWORD@127.0.0.1:3306/chhabi
STATIC_ROOT=/opt/chhabi/shared/staticfiles
MEDIA_URL=/media/
MEDIA_ROOT=/opt/chhabi/shared/media
```

URL-encode reserved password characters such as `@ : / # %`. Quote values
containing shell metacharacters. Never commit `.env`.

## 7. Configure internal MariaDB

```bash
sudo systemctl enable --now mariadb
sudo mariadb-secure-installation
sudo mariadb
```

Run inside the MariaDB prompt, using your own strong password:

```sql
CREATE DATABASE chhabi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'chhabi_app'@'localhost' IDENTIFIED BY 'YOUR_STRONG_DB_PASSWORD';
GRANT ALL PRIVILEGES ON chhabi.* TO 'chhabi_app'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Test the internal database:

```bash
mariadb -h 127.0.0.1 -P 3306 -u chhabi_app -p \
  -e 'SELECT VERSION();' chhabi
```

## 8. Install and initialize Django

```bash
sudo -u chhabi /opt/chhabi/venv/bin/python -m pip install \
  --upgrade pip setuptools wheel
sudo -u chhabi /opt/chhabi/venv/bin/python -m pip install \
  -r /opt/chhabi/app/requirements.txt

sudo -u chhabi bash -c '
  set -e
  set -a; source /opt/chhabi/shared/.env; set +a
  cd /opt/chhabi/app
  /opt/chhabi/venv/bin/python manage.py check --deploy
  /opt/chhabi/venv/bin/python manage.py migrate --noinput
  /opt/chhabi/venv/bin/python manage.py collectstatic --noinput
'
```

Only for a new/empty DB:

```bash
sudo -u chhabi bash -c '
  set -a; source /opt/chhabi/shared/.env; set +a
  cd /opt/chhabi/app
  /opt/chhabi/venv/bin/python manage.py createsuperuser
'
```

Do not use the old `entrypoint.sh`: it runs `makemigrations` and creates a
known-password admin during startup.

## 8. Enable Gunicorn service

```bash
sudo cp /opt/chhabi/app/deploy/aws/chhabi.service \
  /etc/systemd/system/chhabi.service
sudo systemctl daemon-reload
sudo systemctl enable --now chhabi
sudo systemctl status chhabi --no-pager
```

The service deliberately uses one Gunicorn process with four threads. This
project starts APScheduler inside Django; multiple processes/instances would
duplicate leave, payroll, attendance, recruitment, asset, and employee jobs.

## 9. Configure AL2023 Nginx

AL2023 uses `/etc/nginx/conf.d/` (not Ubuntu `sites-available`).

```bash
sudo sed 's/hr\.example\.com/YOUR_REAL_DOMAIN/g' \
  /opt/chhabi/app/deploy/aws/nginx.conf \
  | sudo tee /etc/nginx/conf.d/chhabi.conf >/dev/null

sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx

curl -I http://127.0.0.1:8000/login
curl -I http://YOUR_REAL_DOMAIN/login
```

## 10. Enable HTTPS

After DNS resolves:

```bash
getent hosts YOUR_REAL_DOMAIN
sudo certbot --nginx -d YOUR_REAL_DOMAIN
sudo certbot renew --dry-run
systemctl list-timers | grep certbot
curl -I https://YOUR_REAL_DOMAIN/login
```

Keep HSTS conservative until every required domain/subdomain works on HTTPS.

## 11. wkhtmltopdf for payroll PDFs (x86_64 only)

The project calls `pdfkit`, but AL2023 has no official wkhtmltopdf package.
Upstream publishes only an Amazon Linux 2 RPM. This compatibility install is
optional and must be tested after OS updates:

```bash
cd /tmp
curl -fL -o wkhtmltox.rpm \
  https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.amazonlinux2.x86_64.rpm
sudo dnf install -y ./wkhtmltox.rpm
wkhtmltopdf --version
rm -f /tmp/wkhtmltox.rpm
```

Never force-install if dependency resolution fails. The main app can run, but
`pdfkit` PDF endpoints will fail until a compatible PDF service is provided.

## 12. Import the existing MySQL DB

Export on the current DB machine:

```bash
mysqldump --single-transaction --routines --triggers \
  -h CURRENT_DB_HOST -u CURRENT_DB_USER -p CURRENT_DB_NAME > chhabi.sql
scp -i YOUR_KEY.pem chhabi.sql ec2-user@YOUR_ELASTIC_IP:/home/ec2-user/
```

Back up the internal DB first if it already has data, then import on EC2:

```bash
mariadb -h 127.0.0.1 -P 3306 -u chhabi_app -p chhabi \
  < /home/ec2-user/chhabi.sql

sudo -u chhabi bash -c '
  set -a; source /opt/chhabi/shared/.env; set +a
  cd /opt/chhabi/app
  /opt/chhabi/venv/bin/python manage.py migrate --noinput
'
rm -f /home/ec2-user/chhabi.sql
```

## 13. Transfer uploaded media

From the current machine:

```bash
rsync -avz -e 'ssh -i YOUR_KEY.pem' media/ \
  ec2-user@YOUR_ELASTIC_IP:/home/ec2-user/chhabi-media/
```

On EC2:

```bash
sudo rsync -a /home/ec2-user/chhabi-media/ /opt/chhabi/shared/media/
sudo chown -R chhabi:chhabi /opt/chhabi/shared/media
sudo find /opt/chhabi/shared/media -type d -exec chmod 755 {} \;
sudo find /opt/chhabi/shared/media -type f -exec chmod 644 {} \;
rm -rf /home/ec2-user/chhabi-media
```

## 14. Verify and update

```bash
sudo systemctl status chhabi nginx --no-pager
sudo journalctl -u chhabi -n 200 --no-pager
sudo tail -n 100 /var/log/nginx/error.log
curl -I https://YOUR_REAL_DOMAIN/login

sudo -u chhabi bash -c '
  set -a; source /opt/chhabi/shared/.env; set +a
  cd /opt/chhabi/app
  /opt/chhabi/venv/bin/python manage.py check --deploy
'
```

Later releases:

```bash
sudo -u chhabi git -C /opt/chhabi/app pull --ff-only
cd /opt/chhabi/app
sudo bash deploy/aws/deploy.sh
```

### If Django admin CSS is missing

`staticfiles/` is generated on the server and should not be committed to Git.
Rebuild it and verify that Nginx can read the generated admin CSS:

```bash
sudo -u chhabi bash -c '
  set -e
  set -a; source /opt/chhabi/shared/.env; set +a
  cd /opt/chhabi/app
  /opt/chhabi/venv/bin/python manage.py collectstatic --noinput
'

sudo test -f /opt/chhabi/shared/staticfiles/admin/css/base.css \
  && echo 'Admin CSS exists'
sudo chmod 755 /opt /opt/chhabi /opt/chhabi/shared \
  /opt/chhabi/shared/staticfiles
sudo find /opt/chhabi/shared/staticfiles -type d -exec chmod 755 {} \;
sudo find /opt/chhabi/shared/staticfiles -type f -exec chmod 644 {} \;
sudo nginx -t
sudo systemctl reload nginx
curl -I http://127.0.0.1/static/admin/css/base.css
curl -I https://YOUR_REAL_DOMAIN/static/admin/css/base.css
```

Both `curl` checks should return `200 OK`. A `404` means the Nginx config/path
is wrong; a `403` means permissions or SELinux policy is blocking access. Check
`sudo nginx -T` and `sudo tail -n 100 /var/log/nginx/error.log`.

Before major releases, dump internal MariaDB and take an EBS snapshot. Back up
both the database and `/opt/chhabi/shared/media`. Ship systemd/Nginx logs to
CloudWatch and use an EC2 IAM role instead of permanent AWS access keys.
