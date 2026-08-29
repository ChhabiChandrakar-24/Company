# Payment Integration Guide

## Overview

This project supports two payment providers through a provider-adapter pattern:

| Provider | SDK / Method | Sandbox Available |
|----------|-------------|-------------------|
| **Razorpay** | `razorpay` Python SDK | Yes (`rzp_test_*` keys) |
| **PhonePe** | REST API (no SDK needed) | Yes (PGTESTPAYUAT) |

All billing logic is provider-independent. The `payments` app handles:
- Order creation
- Frontend payment verification
- Webhook signature verification
- Idempotent subscription activation
- Payment history

---

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Frontend   │────>│  CreatePayment   │────>│  Provider Adapter   │
│  (checkout) │     │  View            │     │  (Razorpay/PhonePe) │
└─────────────┘     └──────────────────┘     └─────────────────────┘
       │                                              │
       │            ┌──────────────────┐              │
       └───────────>│  VerifyPayment   │<─────────────┘
                    │  View            │
                    └──────────────────┘

Provider Webhooks:
┌─────────────────┐     ┌───────────────────┐     ┌──────────────────┐
│  Razorpay /     │────>│  Webhook View     │────>│  Activate Sub    │
│  PhonePe Server │     │  (verify sig +    │     │  (idempotent)    │
└─────────────────┘     │   idempotency)    │     └──────────────────┘
                        └───────────────────┘
```

---

## Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/billing/pay/` | Create a payment order |
| POST | `/billing/verify/` | Verify frontend callback |
| POST | `/billing/webhook/razorpay/` | Razorpay webhook receiver |
| POST | `/billing/webhook/phonepe/` | PhonePe webhook receiver |

---

## Environment Variables

Add these to your `.env` file:

### Razorpay

| Variable | Description |
|----------|-------------|
| `RAZORPAY_KEY_ID` | API Key ID from Razorpay Dashboard |
| `RAZORPAY_KEY_SECRET` | API Key Secret |
| `RAZORPAY_WEBHOOK_SECRET` | Webhook secret configured in Razorpay Dashboard > Webhooks |

**Sandbox keys**: Start with `rzp_test_`. Get them from https://dashboard.razorpay.com/app/keys

### PhonePe

| Variable | Description |
|----------|-------------|
| `PHONEPE_MERCHANT_ID` | Merchant ID from PhonePe dashboard |
| `PHONEPE_SALT_KEY` | Salt key for checksum generation |
| `PHONEPE_SALT_INDEX` | Salt index (usually `1`) |
| `PHONEPE_ENV` | `sandbox` or `production` |

**Sandbox values**: Use `PGTESTPAYUAT` as merchant ID. See https://developer.phonepe.com/docs

---

## Security Model

1. **Backend verification**: Frontend payment confirmations are always re-verified
   server-side before activating subscriptions.

2. **Webhook signature verification**: Both providers' webhooks are verified using
   their official signature mechanisms before processing.

3. **Idempotency**: The `external_payment_id` field has a unique constraint.
   Duplicate webhooks are detected via `webhook_processed_at` and silently
   ignored.

4. **Atomic activation**: `activate_subscription_from_payment()` uses
   `select_for_update()` inside a transaction to prevent race conditions.

5. **Credentials in env**: All secrets are loaded from environment variables,
   never committed to version control.

---

## Switching to Production

1. Replace sandbox keys in `.env` with live credentials.
2. Set `PHONEPE_ENV=production`.
3. Configure webhook URLs in provider dashboards:
   - Razorpay: `https://yourdomain.com/billing/webhook/razorpay/`
   - PhonePe: `https://yourdomain.com/billing/webhook/phonepe/`
4. Ensure `RAZORPAY_WEBHOOK_SECRET` matches the secret in your Razorpay webhook config.

---

## Running Tests

```bash
python manage.py test payments
```

Tests cover:
- Successful payment → subscription activation
- Failed payment → subscription stays pending
- Duplicate webhook → silently ignored
- Invalid signature → 400 response
- Subscription activated exactly once (idempotency)

---

## API Usage Example

### 1. Create Payment

```bash
curl -X POST http://localhost:8000/billing/pay/ \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "razorpay",
    "subscription_id": 1,
    "callback_url": "http://localhost:8000/billing/webhook/razorpay/"
  }'
```

### 2. Frontend completes checkout using the returned payload

### 3. Verify from frontend (Razorpay)

```bash
curl -X POST http://localhost:8000/billing/verify/ \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "razorpay",
    "razorpay_order_id": "order_xxx",
    "razorpay_payment_id": "pay_xxx",
    "razorpay_signature": "sig_xxx"
  }'
```

### 4. Webhook is also processed server-side (belt and suspenders)
