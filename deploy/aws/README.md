# Chhabi deployment on AWS EC2

This runbook targets one Ubuntu 24.04 LTS EC2 instance, Amazon RDS MySQL 8,
Nginx, Gunicorn, systemd, an Elastic IP, and HTTPS. Commands assume the app is
installed at `/opt/chhabi/app` and the domain is `hr.example.com`; replace both
where appropriate.

## 1. Create the AWS resources

1. Create an EC2 instance in the intended AWS Region and VPC:
   - Ubuntu Server 24.04 LTS, x86_64.
   - Start with `t3.medium` (2 vCPU, 4 GiB RAM). Increase after observing RAM
     and CPU; PDF/pandas workloads are heavier than a minimal Django app.
   - Use at least a 30 GiB encrypted gp3 EBS volume.
   - EC2 security group inbound rules: SSH/22 from your fixed IP only, HTTP/80
     and HTTPS/443 from the internet. Do not expose port 8000.
   - Allocate and associate an Elastic IP.
2. Create an RDS MySQL 8 instance in the same VPC:
   - Set **Public access: No**.
   - Enable automated backups and encryption.
   - Create database `chhabi` and application user `chhabi_app`.
   - Its security group should allow TCP/3306 only from the EC2 security group.
3. In Route 53 (or the current DNS provider), point an `A` record such as
   `hr.example.com` to the Elastic IP.

## 2. Prepare the Linux server

Connect using EC2 Instance Connect or SSH, then run:

```bash
sudo apt update
sudo apt -y upgrade
sudo apt install -y git nginx python3 python3-venv python3-dev \
  build-essential pkg-config default-libmysqlclient-dev libjpeg-dev zlib1g-dev \
  libffi-dev libssl-dev wkhtmltopdf mysql-client certbot python3-certbot-nginx

sudo adduser --system --group --home /opt/chhabi chhabi
sudo install -d -o chhabi -g chhabi /opt/chhabi/app /opt/chhabi/shared/media \
  /opt/chhabi/shared/staticfiles
sudo -u chhabi python3 -m venv /opt/chhabi/venv
```

`wkhtmltopdf` is required because payroll/base PDF generation uses `pdfkit`.

## 3. Upload the code

Preferred method (private Git repository):

```bash
sudo -u chhabi git clone YOUR_PRIVATE_REPOSITORY_URL /opt/chhabi/app
```

For a later update:

```bash
sudo -u chhabi git -C /opt/chhabi/app pull --ff-only
```

Do not upload `.venv`, `.env`, browser profiles, caches, local logs, or the
local database. Keep `/opt/chhabi/shared` outside the Git checkout.

## 4. Create production secrets

Copy the template and edit it as root:

```bash
sudo cp /opt/chhabi/app/deploy/aws/env.production.example /opt/chhabi/shared/.env
sudo chmod 600 /opt/chhabi/shared/.env
sudo nano /opt/chhabi/shared/.env
```

Generate independent random values:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(64))'
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Set at minimum `SECRET_KEY`, `DB_INIT_PASSWORD`, `ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS`, and the RDS `DATABASE_URL`. If the database password
contains URL-reserved characters (`@`, `:`, `/`, `#`, `%`), URL-encode it.
Quote values that contain shell metacharacters. Never commit the resulting
`.env` file.

## 5. Install and initialize the application

For the first deployment, run the application commands before enabling the
service:

```bash
sudo -u chhabi /opt/chhabi/venv/bin/python -m pip install --upgrade pip setuptools wheel
sudo -u chhabi /opt/chhabi/venv/bin/python -m pip install -r /opt/chhabi/app/requirements.txt

sudo -u chhabi bash -c 'set -a; source /opt/chhabi/shared/.env; set +a; cd /opt/chhabi/app; /opt/chhabi/venv/bin/python manage.py check --deploy'
sudo -u chhabi bash -c 'set -a; source /opt/chhabi/shared/.env; set +a; cd /opt/chhabi/app; /opt/chhabi/venv/bin/python manage.py migrate --noinput'
sudo -u chhabi bash -c 'set -a; source /opt/chhabi/shared/.env; set +a; cd /opt/chhabi/app; /opt/chhabi/venv/bin/python manage.py collectstatic --noinput'
```

Create an admin only if existing production data is not being imported:

```bash
sudo -u chhabi bash -c 'set -a; source /opt/chhabi/shared/.env; set +a; cd /opt/chhabi/app; /opt/chhabi/venv/bin/python manage.py createsuperuser'
```

Do not use `entrypoint.sh` in production: it runs `makemigrations` and creates
an admin with a known password on every start.

## 6. Install systemd and Nginx configuration

```bash
sudo cp /opt/chhabi/app/deploy/aws/chhabi.service /etc/systemd/system/chhabi.service
sudo sed 's/hr\.example\.com/YOUR_REAL_DOMAIN/g' \
  /opt/chhabi/app/deploy/aws/nginx.conf | sudo tee /etc/nginx/sites-available/chhabi >/dev/null
sudo ln -sfn /etc/nginx/sites-available/chhabi /etc/nginx/sites-enabled/chhabi
sudo rm -f /etc/nginx/sites-enabled/default

sudo systemctl daemon-reload
sudo systemctl enable --now chhabi
sudo nginx -t
sudo systemctl enable --now nginx
```

The service deliberately uses one Gunicorn process with four threads. Several
apps start APScheduler inside the Django process; using multiple workers or
multiple EC2 instances currently duplicates payroll, attendance, leave, asset,
and other scheduled jobs.

## 7. Enable HTTPS

Wait until DNS resolves to the Elastic IP, then run:

```bash
sudo certbot --nginx -d YOUR_REAL_DOMAIN
sudo certbot renew --dry-run
```

After HTTPS works, keep `DEBUG=False`, confirm `CSRF_TRUSTED_ORIGINS` starts
with `https://`, and run `manage.py check --deploy` again. Increase HSTS slowly;
do not enable preload until every subdomain is permanently HTTPS-capable.

## 8. Move existing MySQL data and uploaded media

Because the current development database is MySQL, export it from the current
machine with MySQL tools (not from Django):

```bash
mysqldump --single-transaction --routines --triggers \
  -h CURRENT_DB_HOST -u CURRENT_DB_USER -p CURRENT_DB_NAME > chhabi.sql
```

Copy the dump to EC2, import it into RDS, then apply newer migrations:

```bash
mysql -h RDS_ENDPOINT -u chhabi_app -p chhabi < chhabi.sql
sudo -u chhabi bash -c 'set -a; source /opt/chhabi/shared/.env; set +a; cd /opt/chhabi/app; /opt/chhabi/venv/bin/python manage.py migrate --noinput'
```

Copy the current `media/` contents to `/opt/chhabi/shared/media/` (for example
with `scp`/`rsync`) and then fix ownership:

```bash
sudo chown -R chhabi:chhabi /opt/chhabi/shared/media
sudo find /opt/chhabi/shared/media -type d -exec chmod 755 {} \;
sudo find /opt/chhabi/shared/media -type f -exec chmod 644 {} \;
```

Take an RDS snapshot before importing over any non-empty destination database.

## 9. Verify and operate

```bash
sudo systemctl status chhabi nginx
sudo journalctl -u chhabi -n 200 --no-pager
curl -I http://127.0.0.1:8000/login
curl -I https://YOUR_REAL_DOMAIN/login
sudo -u chhabi bash -c 'set -a; source /opt/chhabi/shared/.env; set +a; cd /opt/chhabi/app; /opt/chhabi/venv/bin/python manage.py check --deploy'
```

For later releases:

```bash
sudo -u chhabi git -C /opt/chhabi/app pull --ff-only
cd /opt/chhabi/app
sudo bash deploy/aws/deploy.sh
```

Back up both RDS and `/opt/chhabi/shared/media`. RDS automated backups do not
contain uploaded files. Use EBS snapshots or a scheduled, encrypted S3 sync for
media backups. Monitor disk, memory, HTTP 5xx responses, certificate renewal,
and the `chhabi` systemd journal with CloudWatch alarms/log shipping.

## Amazon Linux 2023 package equivalent

If the existing EC2 host is Amazon Linux 2023 rather than Ubuntu, replace the
`apt` package step with the following and install Certbot according to its
current instructions for that OS:

```bash
sudo dnf update -y
sudo dnf install -y git nginx python3 python3-devel gcc gcc-c++ make \
  pkgconf-pkg-config mariadb105-devel libjpeg-turbo-devel zlib-devel \
  libffi-devel openssl-devel
```

Amazon Linux Nginx uses `/etc/nginx/conf.d/chhabi.conf` instead of the Ubuntu
`sites-available/sites-enabled` layout; copy `deploy/aws/nginx.conf` there.
