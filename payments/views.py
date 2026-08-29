"""
Payment views — order creation + webhook receivers for Razorpay and PhonePe.

All endpoints perform backend verification; frontend payment success is never
trusted on its own.
"""

import json
import logging

from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import PaymentTransaction
from .providers import get_provider
from .services import activate_subscription_from_payment

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Create Order / Initiate Payment
# ---------------------------------------------------------------------------
@method_decorator(csrf_exempt, name="dispatch")
class CreatePaymentView(View):
    """POST /billing/pay/

    Body (JSON):
        {
            "provider": "razorpay" | "phonepe",
            "subscription_id": <int>,
            "callback_url": "<optional>",
            "redirect_url": "<optional>"
        }

    Returns the provider-specific payload the frontend needs to launch the
    checkout flow (Razorpay Checkout.js options or PhonePe redirect URL).
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        provider_name = data.get("provider", "")
        subscription_id = data.get("subscription_id")

        if not provider_name or not subscription_id:
            return JsonResponse(
                {"error": "provider and subscription_id are required"}, status=400
            )

        # Fetch subscription
        from pms.models import UserSubscription

        try:
            sub = UserSubscription.objects.get(pk=subscription_id)
        except UserSubscription.DoesNotExist:
            return JsonResponse({"error": "Subscription not found"}, status=404)

        # Amount in paise (INR smallest unit)
        amount_paise = int(sub.plan.price_inr * 100)
        if amount_paise <= 0:
            return JsonResponse({"error": "Plan price must be > 0"}, status=400)

        try:
            provider = get_provider(provider_name)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        receipt = f"sub_{sub.pk}_{int(timezone.now().timestamp())}"

        try:
            result = provider.create_order(
                amount_paise=amount_paise,
                currency="INR",
                receipt=receipt,
                callback_url=data.get("callback_url", ""),
                redirect_url=data.get("redirect_url", ""),
                user_id=str(request.user.pk) if request.user.is_authenticated else "anon",
            )
        except Exception:
            logger.exception("Failed to create order with %s", provider_name)
            return JsonResponse({"error": "Provider error"}, status=502)

        # Persist a pending transaction
        PaymentTransaction.objects.create(
            provider=provider_name,
            external_payment_id=result["order_id"],
            user_subscription=sub,
            amount=sub.plan.price_inr,
            currency="INR",
            status="pending",
        )

        return JsonResponse({"status": "ok", **result})


# ---------------------------------------------------------------------------
# Verify callback from frontend (Razorpay specific)
# ---------------------------------------------------------------------------
@method_decorator(csrf_exempt, name="dispatch")
class VerifyPaymentView(View):
    """POST /billing/verify/

    Body (JSON):
        Razorpay: { "razorpay_order_id", "razorpay_payment_id", "razorpay_signature" }
        PhonePe:  { "transactionId" }
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        provider_name = data.get("provider", "")
        if not provider_name:
            return JsonResponse({"error": "provider is required"}, status=400)

        try:
            provider = get_provider(provider_name)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        if not provider.verify_payment(data):
            return JsonResponse({"error": "Payment verification failed"}, status=400)

        # Find the pending transaction
        order_id = data.get("razorpay_order_id") or data.get("transactionId", "")
        try:
            txn = PaymentTransaction.objects.get(external_payment_id=order_id)
        except PaymentTransaction.DoesNotExist:
            return JsonResponse({"error": "Transaction not found"}, status=404)

        if txn.status == "completed":
            return JsonResponse({"status": "already_activated"})

        # Update payment id to the actual razorpay payment id if available
        if data.get("razorpay_payment_id"):
            txn.external_payment_id = data["razorpay_payment_id"]

        txn.status = "completed"
        txn.webhook_processed_at = timezone.now()
        txn.save()

        activate_subscription_from_payment(txn)

        return JsonResponse({"status": "ok", "message": "Payment verified and subscription activated"})


# ---------------------------------------------------------------------------
# Razorpay Webhook
# ---------------------------------------------------------------------------
@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(View):
    """POST /billing/webhook/razorpay/

    Razorpay sends ``payment.captured``, ``payment.failed``, etc.
    """

    def post(self, request):
        provider = get_provider("razorpay")

        # 1. Verify signature
        if not provider.verify_webhook_signature(request.body, request.headers):
            logger.warning("Razorpay webhook: invalid signature")
            return JsonResponse({"error": "Invalid signature"}, status=400)

        # 2. Parse payload
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        event = payload.get("event", "")
        payment_id = provider.extract_payment_id(payload)

        if not payment_id:
            return JsonResponse({"error": "No payment id in payload"}, status=400)

        # 3. Idempotency — already processed?
        txn = PaymentTransaction.objects.filter(external_payment_id=payment_id).first()
        if txn and txn.webhook_processed_at is not None:
            logger.info("Razorpay webhook duplicate for %s — skipping", payment_id)
            return JsonResponse({"status": "duplicate"})

        # 4. Match to pending transaction by order id
        order_id = (
            payload.get("payload", {})
            .get("payment", {})
            .get("entity", {})
            .get("order_id", "")
        )

        if not txn and order_id:
            txn = PaymentTransaction.objects.filter(external_payment_id=order_id).first()

        if not txn:
            logger.warning("Razorpay webhook: no matching transaction for %s", payment_id)
            return JsonResponse({"status": "no_match"}, status=200)

        # 5. Process event
        if event == "payment.captured":
            txn.external_payment_id = payment_id
            txn.status = "completed"
            txn.webhook_processed_at = timezone.now()
            txn.save()
            activate_subscription_from_payment(txn)
        elif event == "payment.failed":
            txn.status = "failed"
            txn.webhook_processed_at = timezone.now()
            txn.save()
        else:
            logger.info("Razorpay webhook: unhandled event %s", event)

        return JsonResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# PhonePe Webhook
# ---------------------------------------------------------------------------
@method_decorator(csrf_exempt, name="dispatch")
class PhonePeWebhookView(View):
    """POST /billing/webhook/phonepe/

    PhonePe sends a callback with X-VERIFY header.
    """

    def post(self, request):
        provider = get_provider("phonepe")

        # 1. Verify signature
        if not provider.verify_webhook_signature(request.body, request.headers):
            logger.warning("PhonePe webhook: invalid signature")
            return JsonResponse({"error": "Invalid signature"}, status=400)

        # 2. Parse payload
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        payment_id = provider.extract_payment_id(payload)
        if not payment_id:
            return JsonResponse({"error": "No transaction id"}, status=400)

        # 3. Idempotency
        txn = PaymentTransaction.objects.filter(external_payment_id=payment_id).first()
        if txn and txn.webhook_processed_at is not None:
            logger.info("PhonePe webhook duplicate for %s — skipping", payment_id)
            return JsonResponse({"status": "duplicate"})

        if not txn:
            logger.warning("PhonePe webhook: no matching transaction for %s", payment_id)
            return JsonResponse({"status": "no_match"}, status=200)

        # 4. Check status with PhonePe API for server-side verification
        is_success = provider.verify_payment({"transactionId": payment_id})

        if is_success:
            txn.status = "completed"
            txn.webhook_processed_at = timezone.now()
            txn.save()
            activate_subscription_from_payment(txn)
        else:
            txn.status = "failed"
            txn.webhook_processed_at = timezone.now()
            txn.save()

        return JsonResponse({"status": "ok"})
