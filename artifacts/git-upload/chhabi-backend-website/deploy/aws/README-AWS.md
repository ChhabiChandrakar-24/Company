# Chhabi production deployment on AWS

This deployment uses one Ubuntu EC2 instance for Django/Gunicorn/Nginx, a
private Amazon RDS PostgreSQL database, private Amazon S3 media storage, and an
Elastic IP plus DNS/HTTPS. The React Native application remains a separately
built Android/iOS client and calls the public HTTPS API.

## 1. AWS resources

Create these resources in the same region and VPC (for example `ap-south-1`):

1. An Ubuntu 24.04 LTS EC2 instance. Start with `t3.medium`, 30 GB gp3 EBS.
2. An Elastic IP attached to EC2.
3. A PostgreSQL RDS instance. Start with `db.t4g.micro` or larger, create the
   initial database `chhabi`, keep **Public access disabled**, enable automated
   backups, and record endpoint/user/password.
4. A private S3 bucket with Block Public Access enabled, versioning enabled,
   and default encryption enabled.
5. A Route 53 `A` record such as `hr.example.com` pointing to the Elastic IP.

Production sizing depends on concurrent users and report workloads. Use
Multi-AZ RDS and at least two EC2 instances behind an ALB when high availability
is required; the single-instance layout is the simplest initial production
deployment.

## 2. Security groups

EC2 security group inbound:

| Port | Source | Purpose |
|---|---|---|
| 22 | Your fixed admin IP only | SSH |
| 80 | `0.0.0.0/0`, `::/0` | HTTP and certificate issuance |
| 443 | `0.0.0.0/0`, `::/0` | HTTPS web/API |

Do not expose ports 8000 or 5432 publicly. RDS inbound must allow PostgreSQL
TCP 5432 **from the EC2 security group ID only**.

## 3. EC2 IAM role for S3

Attach an instance role with this policy, replacing the bucket name. Do not put
long-lived AWS keys in `.env`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListMediaBucket",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::CHANGE_ME-chhabi-media",
      "Condition": {"StringLike": {"s3:prefix": ["private", "private/*"]}}
    },
    {
      "Sid": "ManagePrivateMedia",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::CHANGE_ME-chhabi-media/private/*"
    }
  ]
}
```

## 4. Upload and bootstrap

SSH into EC2, upload/clone this repository to `/opt/chhabi/app`, then run from
the repository root:

```bash
sudo bash deploy/aws/bootstrap-ubuntu.sh
sudo cp deploy/aws/chhabi.env.example /opt/chhabi/shared/.env
sudo nano /opt/chhabi/shared/.env
```

Generate a Django secret rather than inventing one:

```bash
/opt/chhabi/venv/bin/python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Fill the domain, RDS endpoint/credentials, bucket and region. Protect the file:

```bash
sudo chown root:chhabi /opt/chhabi/shared/.env
sudo chmod 640 /opt/chhabi/shared/.env
sudo bash deploy/aws/deploy-release.sh
```

The deploy command installs all Python dependencies, runs Django's production
check, applies database migrations, collects static files and starts services.
Create the first administrator interactively once:

```bash
set -a; source /opt/chhabi/shared/.env; set +a
sudo -u chhabi --preserve-env /opt/chhabi/venv/bin/python /opt/chhabi/app/manage.py createsuperuser
```

## 5. Domain and HTTPS

Replace `hr.example.com` in `/etc/nginx/sites-available/chhabi`, verify DNS has
propagated, then run:

```bash
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d hr.example.com
sudo certbot renew --dry-run
```

Verify `https://hr.example.com/health/` returns `{"status": "ok"}`.

## 6. Mobile application

Set both URLs in `mobile/src/config.ts` to the public API for release builds:

```ts
export const API_BASE_URL = 'https://hr.example.com/api';
export const WEB_BASE_URL = 'https://hr.example.com';
```

Then build Android from a development machine (Android Studio/JDK 17/Node 22):

```powershell
cd mobile
npm ci
npm run typecheck
npm run build:android:release
```

The output Android App Bundle is under
`mobile/android/app/build/outputs/bundle/release/`. Configure a private upload
keystore before Play Store release as documented in `mobile/README.md`.

## 7. Operations

```bash
sudo systemctl status chhabi nginx
sudo journalctl -u chhabi -f
sudo systemctl restart chhabi
curl -fsS https://hr.example.com/health/
```

RDS automated backups and S3 versioning protect data, but restoration should be
tested. Add CloudWatch alarms for EC2 CPU/disk, RDS CPU/storage/connections and
HTTP 5xx. Never commit `/opt/chhabi/shared/.env`, database passwords, signing
keys, or AWS credentials.
