"""
Service layer — business logic for activating subscriptions after payment.
"""

import logging

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def activate_subscription_from_payment(payment_txn):
    """Activate the linked UserSubscription after a verified payment.

    Uses select_for_update to prevent concurrent activation from duplicate
    webhook deliveries.
    """
    from pms.models import UserSubscription

    with transaction.atomic():
        sub = (
            UserSubscription.objects
            .select_for_update()
            .get(pk=payment_txn.user_subscription_id)
        )

        if sub.status == "active":
            logger.info(
                "Subscription %s already active — skipping duplicate activation.",
                sub.pk,
            )
            return sub

        sub.status = "active"
        sub.payment_gateway = payment_txn.provider
        sub.external_subscription_id = payment_txn.external_payment_id
        sub.start_date = timezone.now()

        # Set end_date based on plan billing cycle
        if hasattr(sub.plan, "billing_cycle_days") and sub.plan.billing_cycle_days:
            from datetime import timedelta

            sub.end_date = sub.start_date + timedelta(days=sub.plan.billing_cycle_days)

        sub.save()
        logger.info("Subscription %s activated via %s.", sub.pk, payment_txn.provider)

    return sub
