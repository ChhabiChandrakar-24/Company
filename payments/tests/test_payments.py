"""
Unit tests for the payments app.

Covers:
- Successful payment flow
- Failed payment flow
- Duplicate webhook idempotency
- Invalid webhook signature rejection
- Subscription activation exactly once
"""

import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory
from django.utils import timezone

from payments.models import PaymentTransaction
from payments.providers import RazorpayProvider, PhonePeProvider
from payments.services import activate_subscription_from_payment
from payments.views import RazorpayWebhookView, PhonePeWebhookView


class PaymentTransactionModelTest(TestCase):
    """Basic model sanity checks."""

    def setUp(self):
        self.user = User.objects.create_user(username="testpay", password="pass1234")
        from pms.models import MeetingPlan, UserSubscription

        self.plan = MeetingPlan.objects.create(
            name="Pro", code="pro_test", price_inr=499, billing_cycle_days=30
        )
        self.sub = UserSubscription.objects.create(
            user=self.user, plan=self.plan, status="pending"
        )

    def test_create_transaction(self):
        txn = PaymentTransaction.objects.create(
            provider="razorpay",
            external_payment_id="pay_test_123",
            user_subscription=self.sub,
            amount=Decimal("499.00"),
        )
        self.assertEqual(txn.status, "pending")
        self.assertIn("pay_test_123", str(txn))

    def test_unique_external_id(self):
        PaymentTransaction.objects.create(
            provider="razorpay",
            external_payment_id="pay_dup",
            user_subscription=self.sub,
            amount=Decimal("499.00"),
        )
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            PaymentTransaction.objects.create(
                provider="razorpay",
                external_payment_id="pay_dup",
                user_subscription=self.sub,
                amount=Decimal("499.00"),
            )


class SubscriptionActivationTest(TestCase):
    """Test the activate_subscription_from_payment service."""

    def setUp(self):
        self.user = User.objects.create_user(username="actuser", password="pass1234")
        from pms.models import MeetingPlan, UserSubscription

        self.plan = MeetingPlan.objects.create(
            name="Enterprise", code="ent_test", price_inr=999, billing_cycle_days=30
        )
        self.sub = UserSubscription.objects.create(
            user=self.user, plan=self.plan, status="pending"
        )
        self.txn = PaymentTransaction.objects.create(
            provider="razorpay",
            external_payment_id="pay_act_1",
            user_subscription=self.sub,
            amount=Decimal("999.00"),
            status="completed",
        )

    def test_activates_subscription(self):
        result = activate_subscription_from_payment(self.txn)
        self.assertEqual(result.status, "active")
        self.assertEqual(result.payment_gateway, "razorpay")
        self.assertIsNotNone(result.end_date)

    def test_idempotent_activation(self):
        """Calling activate twice does not fail or duplicate."""
        activate_subscription_from_payment(self.txn)
        result = activate_subscription_from_payment(self.txn)
        self.assertEqual(result.status, "active")


class RazorpayWebhookTest(TestCase):
    """Test Razorpay webhook endpoint."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="rzpuser", password="pass1234")
        from pms.models import MeetingPlan, UserSubscription

        self.plan = MeetingPlan.objects.create(
            name="Basic", code="basic_rzp", price_inr=299, billing_cycle_days=30
        )
        self.sub = UserSubscription.objects.create(
            user=self.user, plan=self.plan, status="pending"
        )
        self.txn = PaymentTransaction.objects.create(
            provider="razorpay",
            external_payment_id="order_rzp_001",
            user_subscription=self.sub,
            amount=Decimal("299.00"),
            status="pending",
        )

    @patch("payments.providers.RazorpayProvider.verify_webhook_signature", return_value=True)
    def test_successful_payment_webhook(self, mock_verify):
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_rzp_success",
                        "order_id": "order_rzp_001",
                    }
                }
            },
        }
        request = self.factory.post(
            "/billing/webhook/razorpay/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.headers = {"X-Razorpay-Signature": "valid_sig"}

        response = RazorpayWebhookView.as_view()(request)
        self.assertEqual(response.status_code, 200)

        self.txn.refresh_from_db()
        self.assertEqual(self.txn.status, "completed")
        self.assertIsNotNone(self.txn.webhook_processed_at)

        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "active")

    @patch("payments.providers.RazorpayProvider.verify_webhook_signature", return_value=True)
    def test_failed_payment_webhook(self, mock_verify):
        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_rzp_fail",
                        "order_id": "order_rzp_001",
                    }
                }
            },
        }
        request = self.factory.post(
            "/billing/webhook/razorpay/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.headers = {"X-Razorpay-Signature": "valid_sig"}

        response = RazorpayWebhookView.as_view()(request)
        self.assertEqual(response.status_code, 200)

        self.txn.refresh_from_db()
        self.assertEqual(self.txn.status, "failed")

        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "pending")

    @patch("payments.providers.RazorpayProvider.verify_webhook_signature", return_value=True)
    def test_duplicate_webhook_ignored(self, mock_verify):
        # First call
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_rzp_dup",
                        "order_id": "order_rzp_001",
                    }
                }
            },
        }
        request = self.factory.post(
            "/billing/webhook/razorpay/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.headers = {"X-Razorpay-Signature": "valid_sig"}
        RazorpayWebhookView.as_view()(request)

        # Second call — should be treated as duplicate
        self.txn.refresh_from_db()
        request2 = self.factory.post(
            "/billing/webhook/razorpay/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request2.headers = {"X-Razorpay-Signature": "valid_sig"}
        response = RazorpayWebhookView.as_view()(request2)

        data = json.loads(response.content)
        self.assertEqual(data["status"], "duplicate")

    @patch("payments.providers.RazorpayProvider.verify_webhook_signature", return_value=False)
    def test_invalid_signature_rejected(self, mock_verify):
        payload = {"event": "payment.captured", "payload": {}}
        request = self.factory.post(
            "/billing/webhook/razorpay/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.headers = {"X-Razorpay-Signature": "bad_sig"}

        response = RazorpayWebhookView.as_view()(request)
        self.assertEqual(response.status_code, 400)


class PhonePeWebhookTest(TestCase):
    """Test PhonePe webhook endpoint."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="ppuser", password="pass1234")
        from pms.models import MeetingPlan, UserSubscription

        self.plan = MeetingPlan.objects.create(
            name="Starter", code="starter_pp", price_inr=199, billing_cycle_days=30
        )
        self.sub = UserSubscription.objects.create(
            user=self.user, plan=self.plan, status="pending"
        )
        self.txn = PaymentTransaction.objects.create(
            provider="phonepe",
            external_payment_id="txn_pp_001",
            user_subscription=self.sub,
            amount=Decimal("199.00"),
            status="pending",
        )

    @patch("payments.providers.PhonePeProvider.verify_webhook_signature", return_value=True)
    @patch("payments.providers.PhonePeProvider.verify_payment", return_value=True)
    def test_successful_phonepe_webhook(self, mock_pay, mock_sig):
        payload = {
            "success": True,
            "code": "PAYMENT_SUCCESS",
            "data": {"merchantTransactionId": "txn_pp_001"},
        }
        request = self.factory.post(
            "/billing/webhook/phonepe/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.headers = {"X-VERIFY": "somechecksum###1"}

        response = PhonePeWebhookView.as_view()(request)
        self.assertEqual(response.status_code, 200)

        self.txn.refresh_from_db()
        self.assertEqual(self.txn.status, "completed")

        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "active")

    @patch("payments.providers.PhonePeProvider.verify_webhook_signature", return_value=False)
    def test_invalid_phonepe_signature(self, mock_sig):
        payload = {"data": {"merchantTransactionId": "txn_pp_001"}}
        request = self.factory.post(
            "/billing/webhook/phonepe/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.headers = {"X-VERIFY": "bad###1"}

        response = PhonePeWebhookView.as_view()(request)
        self.assertEqual(response.status_code, 400)


class ProviderRegistryTest(TestCase):
    """Test the get_provider helper."""

    def test_unknown_provider_raises(self):
        from payments.providers import get_provider

        with self.assertRaises(ValueError):
            get_provider("stripe")
