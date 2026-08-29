import datetime
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from .models import UserSubscription, EntitlementLog, FeatureFlag


class EntitlementError(PermissionDenied):
    """Custom exception raised when a subscription entitlement is not satisfied."""

    status_code = 403
    default_detail = "Subscription entitlement not met."

    def __init__(self, detail=None, status_code=None):
        self.detail = detail or self.default_detail
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.detail)

    def get_response(self):
        return JsonResponse({"error": "entitlement", "detail": self.detail}, status=self.status_code)


class EntitlementService:
    """Service attached to ``request`` for checking feature flags and consuming quotas.

    Usage in a view::

        request.entitlement.check_feature('developer_api')
        request.entitlement.consume_quota('rooms_created_today')
    """

    def __init__(self, request):
        self.request = request
        # ``require_developer_api_key`` decorator attaches ``developer_subscription``
        self.subscription = getattr(request, "developer_subscription", None)
        if not self.subscription:
            # Check active subscription for the resolved organization first
            org = getattr(request, "organization", None)
            if org:
                self.subscription = (
                    UserSubscription.objects.filter(organization=org, status="active")
                    .select_related("plan")
                    .first()
                )
        if not self.subscription:
            # Fallback to any active subscription for the user
            user = getattr(request, "developer_user", None) or (request.user if request.user.is_authenticated else None)
            if user:
                self.subscription = (
                    UserSubscription.objects.filter(user=user, status="active")
                    .select_related("plan")
                    .first()
                )
        self.plan = self.subscription.plan if self.subscription else None

    def _log(self, action, **kwargs):
        if not self.subscription:
            return
        EntitlementLog.objects.create(
            subscription=self.subscription,
            action=action,
            **kwargs,
        )

    def check_feature(self, feature_name: str):
        """Validate that the current subscription plan enables ``feature_name``.

        ``feature_name`` must correspond to a ``FeatureFlag`` entry attached to the plan.
        Raises :class:`EntitlementError` if the feature is disabled.
        """
        if not self.subscription:
            raise EntitlementError("No active subscription found for your organization.", status_code=403)
        # Compatibility: direct boolean fields on the plan (e.g., allow_developer_api)
        boolean_field = f"allow_{feature_name}"
        if hasattr(self.plan, boolean_field):
            if getattr(self.plan, boolean_field):
                self._log(action="feature_check", feature_name=feature_name, success=True)
                return True
        # Lookup FeatureFlag record
        try:
            flag = FeatureFlag.objects.get(plan=self.plan, feature_name=feature_name)
            if flag.enabled:
                self._log(action="feature_check", feature_name=feature_name, success=True)
                return True
        except FeatureFlag.DoesNotExist:
            pass
        self._log(action="feature_check", feature_name=feature_name, success=False)
        raise EntitlementError(f"Feature '{feature_name}' is not enabled for your subscription.", status_code=403)

    def consume_quota(self, quota_type: str, amount: int = 1):
        """Consume a quota on the subscription.

        ``quota_type`` should match a numeric usage field on ``UserSubscription`` (e.g.
        ``rooms_created_today`` or ``api_calls_today``). The method increments the field and
        raises ``EntitlementError`` with HTTP 429 if the quota would be exceeded.
        """
        if not self.subscription:
            raise EntitlementError("No active subscription found for your organization.", status_code=403)
        current = getattr(self.subscription, quota_type, None)
        if current is None:
            raise EntitlementError(f"Quota type '{quota_type}' not found on subscription.", status_code=400)
        # Map quota types to limit names
        quota_to_limit = {
            "rooms_created_today": "rooms_limit",
            "api_calls_today": "api_calls_limit",
            "storage_used_mb": "storage_limit_mb",
        }
        limit_field_name = quota_to_limit.get(quota_type)
        if limit_field_name is None:
            limit_field_name = f"max_{quota_type}"
            
        # Try to get override limit from the subscription first
        limit = getattr(self.subscription, limit_field_name, None)
        if limit is None or limit == 0:
            # Fallback to plan limits (mapped to the plan's field names)
            plan_field_map = {
                "rooms_limit": "max_concurrent_rooms",
                "api_calls_limit": "max_api_calls_per_day",
                "storage_limit_mb": "storage_limit_mb",
            }
            plan_field = plan_field_map.get(limit_field_name, limit_field_name)
            limit = getattr(self.plan, plan_field, None)

        if limit is not None and (current + amount) > limit:
            self._log(action="quota_consume", quota_type=quota_type, amount=amount, success=False)
            raise EntitlementError(f"Quota exceeded for {quota_type}. Limit: {limit}", status_code=429)
        # Increment and persist
        setattr(self.subscription, quota_type, current + amount)
        self.subscription.save(update_fields=[quota_type])
        self._log(action="quota_consume", quota_type=quota_type, amount=amount, success=True)
        return True
