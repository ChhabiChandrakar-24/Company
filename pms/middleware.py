from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone

class DeveloperRateLimitMiddleware(MiddlewareMixin):
    """Simple per-API-key rate limiting middleware.
    Reads the ``rate_limit_per_minute`` attribute from the ``DeveloperApiKey`` model.
    Uses Django's default cache (local-memory in dev) to store a request count per key.
    Returns HTTP 429 when limit exceeded.
    """
    def process_request(self, request):
        # The ``require_developer_api_key`` decorator attaches ``developer_app`` to request.
        api_key_obj = getattr(request, "developer_app", None)
        if not api_key_obj:
            # No API key present; let other auth handle (e.g., 401).
            return None
        limit = getattr(api_key_obj, "rate_limit_per_minute", None)
        if not limit:
            return None
        cache_key = f"rl:{api_key_obj.api_key}"
        data = cache.get(cache_key)
        now = timezone.now()
        if data:
            count, reset = data
            if now >= reset:
                # Reset window
                count = 0
                reset = now + timezone.timedelta(minutes=1)
        else:
            count = 0
            reset = now + timezone.timedelta(minutes=1)
        if count >= limit:
            retry_after = int((reset - now).total_seconds())
            return JsonResponse({"detail": "Rate limit exceeded"}, status=429, headers={"Retry-After": str(retry_after)})
        # Increment count and store
        cache.set(cache_key, (count + 1, reset), timeout=int((reset - now).total_seconds()))
        # Initialize entitlement service for downstream views
        from pms.entitlement import EntitlementService
        request.entitlement = EntitlementService(request)
        # Consume API call quota for this request
        request.entitlement.consume_quota('api_calls_today')
        return None


class TenantMiddleware(MiddlewareMixin):
    """SaaS Tenancy Context middleware.
    Resolves the current active organization and attaches it to the request.
    Also initializes request.entitlement for view limits check.
    """
    def process_request(self, request):
        if request.user.is_authenticated:
            # Check session for active org id
            org_id = request.session.get("active_organization_id")
            membership = None
            if org_id:
                membership = request.user.organization_memberships.filter(
                    organization_id=org_id
                ).select_related("organization").first()
            
            if not membership:
                # Default to the first organization they belong to
                membership = request.user.organization_memberships.select_related("organization").first()
            
            if membership:
                request.organization = membership.organization
                request.organization_role = membership.role
                request.session["active_organization_id"] = membership.organization.id
            else:
                request.organization = None
                request.organization_role = None
        else:
            request.organization = None
            request.organization_role = None
            
        # Instantiate EntitlementService so it's always accessible in templates / views
        from pms.entitlement import EntitlementService
        request.entitlement = EntitlementService(request)
        return None

