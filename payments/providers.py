"""
Abstract payment provider interface and concrete adapters for Razorpay and PhonePe.

All provider-specific logic is isolated here so that the rest of the billing
system never imports provider SDKs directly.
"""

import abc
import hashlib
import base64
import hmac
import json
import logging
import uuid

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------
class BasePaymentProvider(abc.ABC):
    """Contract that every payment provider adapter must satisfy."""

    @abc.abstractmethod
    def create_order(self, amount_paise: int, currency: str, receipt: str, **kwargs) -> dict:
        """Create an order / initiate a payment session.

        Returns a dict with at least:
            - order_id: str  (provider-side order/transaction id)
            - payload:  dict (data the frontend needs to complete checkout)
        """

    @abc.abstractmethod
    def verify_payment(self, payload: dict) -> bool:
        """Verify a payment callback coming from the frontend.

        Returns True when the signature is cryptographically valid.
        """

    @abc.abstractmethod
    def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
        """Verify the signature on an incoming webhook request.

        Returns True when valid.
        """

    @abc.abstractmethod
    def extract_payment_id(self, payload: dict) -> str:
        """Pull the canonical payment/transaction id out of a webhook payload."""


# ---------------------------------------------------------------------------
# Razorpay adapter
# ---------------------------------------------------------------------------
class RazorpayProvider(BasePaymentProvider):
    """Adapter for the Razorpay Payments API.

    Requires ``razorpay`` Python SDK and the following Django settings:
        - RAZORPAY_KEY_ID
        - RAZORPAY_KEY_SECRET
    """

    def __init__(self):
        import razorpay

        self.key_id = getattr(settings, "RAZORPAY_KEY_ID", "")
        self.key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
        self.client = razorpay.Client(auth=(self.key_id, self.key_secret))

    # -- create order -------------------------------------------------------
    def create_order(self, amount_paise: int, currency: str = "INR", receipt: str = "", **kwargs) -> dict:
        order_data = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt or str(uuid.uuid4()),
            "payment_capture": 1,
        }
        order = self.client.order.create(data=order_data)
        return {
            "order_id": order["id"],
            "payload": {
                "key": self.key_id,
                "amount": amount_paise,
                "currency": currency,
                "order_id": order["id"],
                "name": getattr(settings, "SITE_NAME", "Horilla"),
            },
        }

    # -- verify frontend callback -------------------------------------------
    def verify_payment(self, payload: dict) -> bool:
        try:
            self.client.utility.verify_payment_signature(payload)
            return True
        except Exception:
            logger.warning("Razorpay signature verification failed", exc_info=True)
            return False

    # -- verify webhook -----------------------------------------------------
    def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
        signature = headers.get("X-Razorpay-Signature", "")
        webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", self.key_secret)
        try:
            self.client.utility.verify_webhook_signature(
                body.decode("utf-8"), signature, webhook_secret
            )
            return True
        except Exception:
            logger.warning("Razorpay webhook signature invalid", exc_info=True)
            return False

    # -- extract id ---------------------------------------------------------
    def extract_payment_id(self, payload: dict) -> str:
        try:
            return payload["payload"]["payment"]["entity"]["id"]
        except (KeyError, TypeError):
            return ""


# ---------------------------------------------------------------------------
# PhonePe adapter
# ---------------------------------------------------------------------------
class PhonePeProvider(BasePaymentProvider):
    """Adapter for the PhonePe Payment Gateway REST API (v1).

    Requires the following Django settings:
        - PHONEPE_MERCHANT_ID
        - PHONEPE_SALT_KEY
        - PHONEPE_SALT_INDEX   (usually "1")
        - PHONEPE_ENV          ("sandbox" | "production")
    """

    SANDBOX_URL = "https://api-preprod.phonepe.com/apis/pg-sandbox"
    PRODUCTION_URL = "https://api.phonepe.com/apis/hermes"

    def __init__(self):
        self.merchant_id = getattr(settings, "PHONEPE_MERCHANT_ID", "")
        self.salt_key = getattr(settings, "PHONEPE_SALT_KEY", "")
        self.salt_index = getattr(settings, "PHONEPE_SALT_INDEX", "1")
        env = getattr(settings, "PHONEPE_ENV", "sandbox")
        self.base_url = self.SANDBOX_URL if env == "sandbox" else self.PRODUCTION_URL

    # -- helpers ------------------------------------------------------------
    def _checksum(self, payload_b64: str, endpoint: str) -> str:
        raw = payload_b64 + endpoint + self.salt_key
        sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"{sha}###{self.salt_index}"

    # -- create order -------------------------------------------------------
    def create_order(self, amount_paise: int, currency: str = "INR", receipt: str = "", **kwargs) -> dict:
        transaction_id = receipt or str(uuid.uuid4())
        callback_url = kwargs.get("callback_url", "")
        redirect_url = kwargs.get("redirect_url", "")

        payload = {
            "merchantId": self.merchant_id,
            "merchantTransactionId": transaction_id,
            "merchantUserId": kwargs.get("user_id", "user"),
            "amount": amount_paise,
            "redirectUrl": redirect_url,
            "redirectMode": "POST",
            "callbackUrl": callback_url,
            "paymentInstrument": {"type": "PAY_PAGE"},
        }

        payload_json = json.dumps(payload)
        payload_b64 = base64.b64encode(payload_json.encode("utf-8")).decode("utf-8")
        endpoint = "/pg/v1/pay"
        checksum = self._checksum(payload_b64, endpoint)

        resp = requests.post(
            f"{self.base_url}{endpoint}",
            json={"request": payload_b64},
            headers={
                "Content-Type": "application/json",
                "X-VERIFY": checksum,
            },
            timeout=30,
        )
        data = resp.json()

        redirect_info = ""
        if data.get("success") and data.get("data", {}).get("instrumentResponse"):
            redirect_info = data["data"]["instrumentResponse"].get("redirectInfo", {}).get("url", "")

        return {
            "order_id": transaction_id,
            "payload": {
                "transaction_id": transaction_id,
                "redirect_url": redirect_info,
                "provider_response": data,
            },
        }

    # -- verify frontend callback -------------------------------------------
    def verify_payment(self, payload: dict) -> bool:
        transaction_id = payload.get("transactionId", "")
        if not transaction_id:
            return False

        endpoint = f"/pg/v1/status/{self.merchant_id}/{transaction_id}"
        raw = endpoint + self.salt_key
        sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        checksum = f"{sha}###{self.salt_index}"

        resp = requests.get(
            f"{self.base_url}{endpoint}",
            headers={
                "Content-Type": "application/json",
                "X-VERIFY": checksum,
                "X-MERCHANT-ID": self.merchant_id,
            },
            timeout=30,
        )
        data = resp.json()
        return data.get("success", False) and data.get("code") == "PAYMENT_SUCCESS"

    # -- verify webhook -----------------------------------------------------
    def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
        x_verify = headers.get("X-VERIFY", "")
        if "###" not in x_verify:
            return False

        received_hash, _ = x_verify.split("###", 1)
        raw = body.decode("utf-8") + self.salt_key
        expected_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return hmac.compare_digest(received_hash, expected_hash)

    # -- extract id ---------------------------------------------------------
    def extract_payment_id(self, payload: dict) -> str:
        return payload.get("data", {}).get("merchantTransactionId", "")


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------
PROVIDERS = {
    "razorpay": RazorpayProvider,
    "phonepe": PhonePeProvider,
}


def get_provider(name: str) -> BasePaymentProvider:
    """Return an instantiated provider adapter by name.

    Raises ValueError for unknown providers.
    """
    cls = PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"Unknown payment provider: {name}")
    return cls()
