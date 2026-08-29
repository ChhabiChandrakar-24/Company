import json
import uuid
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from pms.models import (
    MeetingPlan,
    UserSubscription,
    PaymentTransaction,
    PaymentGatewayConfig,
)
from pms.payment_gateways import (
    RazorpayGateway,
    PhonePeGateway,
    get_gateway_credentials,
)


def seed_default_plans_if_empty():
    """Ensure standard meeting plans exist in the system."""
    if MeetingPlan.objects.exists():
        return

    plans = [
        {
            "name": "Free / Trial",
            "code": "free",
            "description": "Ideal for quick one-on-one video calls and small team syncs.",
            "plan_type": "free",
            "price_inr": Decimal("0.00"),
            "billing_cycle_days": 30,
            "max_participants": 2,
            "max_duration_minutes": 40,
            "allow_cloud_recording": False,
            "allow_screen_share": True,
            "allow_captions": True,
            "allow_developer_api": False,
            "max_api_calls_per_day": 50,
            "max_concurrent_rooms": 1,
            "badge_text": "Free",
        },
        {
            "name": "Peer-to-Peer Starter",
            "code": "p2p_starter",
            "description": "Unlimited 1-on-1 P2P video calls with custom branding and recording.",
            "plan_type": "p2p_monthly",
            "price_inr": Decimal("499.00"),
            "per_seat_price_inr": Decimal("199.00"),
            "billing_cycle_days": 30,
            "max_participants": 5,
            "max_duration_minutes": 180,
            "allow_cloud_recording": True,
            "allow_screen_share": True,
            "allow_captions": True,
            "allow_developer_api": True,
            "max_api_calls_per_day": 1000,
            "max_concurrent_rooms": 3,
            "is_popular": True,
            "badge_text": "Popular P2P",
        },
        {
            "name": "Pro Multi-Party Monthly",
            "code": "pro_monthly",
            "description": "Full Zoom-like conference room with up to 50 participants, cloud recording, and Developer API.",
            "plan_type": "pro_monthly",
            "price_inr": Decimal("1499.00"),
            "billing_cycle_days": 30,
            "max_participants": 50,
            "max_duration_minutes": 720,
            "allow_cloud_recording": True,
            "allow_screen_share": True,
            "allow_captions": True,
            "allow_developer_api": True,
            "max_api_calls_per_day": 5000,
            "max_concurrent_rooms": 10,
            "badge_text": "Business",
        },
        {
            "name": "Enterprise Annual",
            "code": "enterprise_annual",
            "description": "Dedicated WebRTC infrastructure, unlimited API access, 500 participants, and 24/7 priority support.",
            "plan_type": "enterprise_annual",
            "price_inr": Decimal("14999.00"),
            "billing_cycle_days": 365,
            "max_participants": 500,
            "max_duration_minutes": 1440,
            "allow_cloud_recording": True,
            "allow_screen_share": True,
            "allow_captions": True,
            "allow_developer_api": True,
            "max_api_calls_per_day": 50000,
            "max_concurrent_rooms": 50,
            "badge_text": "Enterprise",
        },
    ]

    for p in plans:
        MeetingPlan.objects.get_or_create(code=p["code"], defaults=p)


def seed_default_gateways_if_empty():
    from pms.models import PaymentGateway
    if not PaymentGateway.objects.exists():
        PaymentGateway.objects.create(
            name="razorpay",
            display_name="Razorpay",
            is_enabled=True,
            is_default=True,
            priority=1,
            is_live=False,
        )
        PaymentGateway.objects.create(
            name="phonepe",
            display_name="PhonePe",
            is_enabled=True,
            is_default=False,
            priority=2,
            is_live=False,
        )


@login_required
def subscription_plans_view(request):
    """
    Renders the subscription pricing table and active subscription status.
    """
    seed_default_plans_if_empty()
    seed_default_gateways_if_empty()
    plans = MeetingPlan.objects.filter(is_active=True, is_archived=False).order_by("price_inr")

    # Get active subscription for current user
    active_sub = (
        UserSubscription.objects.filter(user=request.user, status="active")
        .order_by("-id")
        .first()
    )

    org = getattr(request, "organization", None)
    plans_data = []
    for plan in plans:
        price = plan.price_inr
        is_custom = False
        if org:
            from pms.models import CustomOffer
            offer = CustomOffer.objects.filter(organization=org, plan=plan, is_active=True).first()
            if offer:
                price = offer.price_override
                is_custom = True
        plans_data.append({
            "plan": plan,
            "display_price": price,
            "is_custom_offer": is_custom,
        })

    from pms.models import PaymentGateway
    active_gateways = PaymentGateway.objects.filter(is_enabled=True)
    default_gw = active_gateways.filter(is_default=True).first()

    context = {
        "plans_data": plans_data,
        "active_subscription": active_sub,
        "user_email": request.user.email,
        "user_name": request.user.get_full_name() or request.user.username,
        "active_gateways": active_gateways,
        "default_gateway": default_gw,
    }
    return render(request, "subscription/plans.html", context)


@login_required
def create_checkout_order(request):
    """
    POST: creates an order for Razorpay or PhonePe and returns checkout payload.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST

    plan_id = data.get("plan_id")
    gateway_name = (data.get("gateway") or "").lower().strip()
    peer_seats = int(data.get("peer_seats", 1))

    plan = get_object_or_404(MeetingPlan, id=plan_id, is_active=True)

    org = getattr(request, "organization", None)
    total_amount = plan.price_inr

    # Check for Custom Offer override
    if org:
        from pms.models import CustomOffer
        offer = CustomOffer.objects.filter(organization=org, plan=plan, is_active=True).first()
        if offer:
            total_amount = offer.price_override

    if plan.plan_type == "p2p_monthly" and peer_seats > 1:
        total_amount += plan.per_seat_price_inr * (peer_seats - 1)

    # Free plan instant activation
    if total_amount <= 0:
        sub = UserSubscription.objects.create(
            user=request.user,
            organization=org,
            plan=plan,
            peer_seats=peer_seats,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=plan.billing_cycle_days),
            status="active",
            payment_gateway="free",
        )
        return JsonResponse({
            "status": "success",
            "is_free": True,
            "message": f"Activated {plan.name} successfully!",
            "subscription_id": sub.id,
        })

    # Resolve Default & Active Gateways
    from pms.models import PaymentGateway, BillingAuditLog
    active_gateways = PaymentGateway.objects.filter(is_enabled=True)
    default_gw = active_gateways.filter(is_default=True).first()

    selected_gw = None
    if gateway_name:
        requested_gw = active_gateways.filter(name=gateway_name).first()
        if requested_gw:
            selected_gw = requested_gw
        else:
            # Log fallback event
            BillingAuditLog.objects.create(
                event_type="gateway_fallback",
                description=f"Requested payment gateway '{gateway_name}' was unavailable. Falling back to system default.",
                performed_by=request.user
            )

    if not selected_gw:
        selected_gw = default_gw or active_gateways.first()

    if not selected_gw:
        return JsonResponse({"error": "No active payment gateways are configured at this time."}, status=400)

    # Log gateway selection event
    BillingAuditLog.objects.create(
        event_type="gateway_selection",
        description=f"Selected gateway '{selected_gw.display_name}' for transaction.",
        performed_by=request.user
    )

    txn_ref = f"TXN_{uuid.uuid4().hex[:12].upper()}"

    # Record Initiated Transaction
    txn = PaymentTransaction.objects.create(
        user=request.user,
        plan=plan,
        amount=total_amount,
        currency="INR",
        gateway=selected_gw.name,
        order_id=txn_ref,
        status="initiated",
        raw_payload={"peer_seats": peer_seats, "plan_code": plan.code},
    )

    if selected_gw.name == "razorpay":
        rzp_order = RazorpayGateway.create_order(
            amount_inr=total_amount,
            receipt_id=txn_ref,
            notes={"user_id": request.user.id, "plan_id": plan.id, "txn_id": txn.id},
        )
        txn.order_id = rzp_order["id"]
        txn.raw_response = rzp_order
        txn.save(update_fields=["order_id", "raw_response"])

        return JsonResponse({
            "status": "success",
            "gateway": "razorpay",
            "order_id": rzp_order["id"],
            "amount_paise": rzp_order["amount"],
            "currency": "INR",
            "key_id": rzp_order.get("key_id"),
            "plan_name": plan.name,
            "user_name": request.user.get_full_name() or request.user.username,
            "user_email": request.user.email,
        })

    elif selected_gw.name == "phonepe":
        redirect_url = request.build_absolute_uri("/pms/subscription/phonepe/callback/")
        callback_url = request.build_absolute_uri("/pms/subscription/phonepe/callback/")

        phonepe_res = PhonePeGateway.create_payment_request(
            amount_inr=total_amount,
            transaction_id=txn_ref,
            user_id=request.user.id,
            redirect_url=redirect_url,
            callback_url=callback_url,
        )
        txn.raw_response = phonepe_res
        txn.save(update_fields=["raw_response"])

        return JsonResponse({
            "status": "success",
            "gateway": "phonepe",
            "pay_url": phonepe_res.get("pay_url"),
            "transaction_id": txn_ref,
        })

    return JsonResponse({"error": "Unsupported payment gateway"}, status=400)


@csrf_exempt
def razorpay_verify_payment(request):
    """
    POST: verifies Razorpay payment signature and activates subscription.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST

    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature", "")

    if not razorpay_order_id or not razorpay_payment_id:
        return JsonResponse({"error": "Missing payment parameters"}, status=400)

    is_valid = RazorpayGateway.verify_payment_signature(
        razorpay_order_id, razorpay_payment_id, razorpay_signature
    )

    from django.db import transaction
    with transaction.atomic():
        txn = PaymentTransaction.objects.select_for_update().filter(order_id=razorpay_order_id).first()
        if not txn:
            return JsonResponse({"error": "Transaction record not found"}, status=404)

        if txn.status == "success":
            if txn.subscription:
                return JsonResponse({
                    "status": "success",
                    "message": "Payment verified and subscription already active.",
                    "subscription_id": txn.subscription.id,
                })
            # If txn succeeded but subscription model was not fully written, we will fall through and create it.

        if is_valid:
            txn.payment_id = razorpay_payment_id
            txn.signature = razorpay_signature
            txn.status = "success"
            txn.save()

            # Create or update active subscription
            plan = txn.plan
            peer_seats = txn.raw_payload.get("peer_seats", 1) if txn.raw_payload else 1

            # Get user organization for scoping if applicable
            org = getattr(request, "organization", None)
            if not org:
                # Fallback to user's first organization
                membership = txn.user.organization_memberships.select_related("organization").first()
                org = membership.organization if membership else None

            sub = UserSubscription.objects.create(
                user=txn.user,
                organization=org,
                plan=plan,
                peer_seats=peer_seats,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=plan.billing_cycle_days),
                status="active",
                payment_gateway="razorpay",
                external_subscription_id=razorpay_payment_id,
            )
            txn.subscription = sub
            txn.save(update_fields=["subscription"])

            return JsonResponse({
                "status": "success",
                "message": f"Payment of ₹{txn.amount} verified! Subscription to {plan.name} is now active.",
                "subscription_id": sub.id,
            })
        else:
            txn.status = "failed"
            txn.error_message = "Signature verification failed"
            txn.save()
            return JsonResponse({"error": "Payment signature verification failed"}, status=400)


@csrf_exempt
def phonepe_callback(request):
    """
    Handles PhonePe PG redirect and webhook callback.
    """
    post_data = request.POST
    txn_id = (
        post_data.get("merchantTransactionId")
        or post_data.get("transactionId")
        or request.GET.get("merchantTransactionId")
    )
    code = post_data.get("code") or request.GET.get("code")

    if not txn_id:
        return HttpResponse("Missing PhonePe transaction reference", status=400)

    from django.db import transaction
    with transaction.atomic():
        txn = PaymentTransaction.objects.select_for_update().filter(order_id=txn_id).first()
        if not txn:
            return HttpResponse("Transaction not found", status=404)

        if txn.status == "success":
            return redirect("/pms/subscription/plans/?payment=success")

        if code == "PAYMENT_SUCCESS" or post_data.get("response"):
            txn.status = "success"
            txn.payment_id = post_data.get("providerReferenceId", txn_id)
            txn.raw_response = dict(post_data)
            txn.save()

            plan = txn.plan
            peer_seats = txn.raw_payload.get("peer_seats", 1) if txn.raw_payload else 1

            # Get organization mapping
            membership = txn.user.organization_memberships.select_related("organization").first()
            org = membership.organization if membership else None

            sub = UserSubscription.objects.create(
                user=txn.user,
                organization=org,
                plan=plan,
                peer_seats=peer_seats,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=plan.billing_cycle_days),
                status="active",
                payment_gateway="phonepe",
                external_subscription_id=txn.payment_id,
            )
            txn.subscription = sub
            txn.save(update_fields=["subscription"])

            return redirect("/pms/subscription/plans/?payment=success")
        else:
            txn.status = "failed"
            txn.error_message = f"PhonePe status code: {code}"
            txn.save()
            return redirect("/pms/subscription/plans/?payment=failed")


@login_required
def transaction_history_view(request):
    """
    Lists payment history, invoices and subscription transactions.
    """
    if request.user.is_superuser:
        transactions = PaymentTransaction.objects.all().select_related("user", "plan")
    else:
        transactions = PaymentTransaction.objects.filter(user=request.user).select_related("plan")

    return render(
        request,
        "subscription/transactions.html",
        {"transactions": transactions},
    )


@login_required
def admin_plans_list(request):
    _require_admin(request)
    plans = MeetingPlan.objects.all().order_by("is_archived", "price_inr")
    return render(request, "subscription/admin_plans.html", {"plans": plans})


@login_required
def admin_plan_create(request):
    _require_admin(request)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip()
        description = request.POST.get("description", "").strip()
        plan_type = request.POST.get("plan_type", "free").strip()
        price_inr = Decimal(request.POST.get("price_inr", "0.00"))
        per_seat_price_inr = Decimal(request.POST.get("per_seat_price_inr", "0.00"))
        billing_cycle_days = int(request.POST.get("billing_cycle_days", 30))
        max_participants = int(request.POST.get("max_participants", 2))
        max_duration_minutes = int(request.POST.get("max_duration_minutes", 40))
        allow_cloud_recording = "allow_cloud_recording" in request.POST
        allow_screen_share = "allow_screen_share" in request.POST
        allow_captions = "allow_captions" in request.POST
        allow_developer_api = "allow_developer_api" in request.POST
        max_api_calls_per_day = int(request.POST.get("max_api_calls_per_day", 100))
        max_concurrent_rooms = int(request.POST.get("max_concurrent_rooms", 1))
        storage_limit_mb = int(request.POST.get("storage_limit_mb", 0))
        is_active = "is_active" in request.POST
        visibility = request.POST.get("visibility", "public").strip()
        is_popular = "is_popular" in request.POST
        badge_text = request.POST.get("badge_text", "").strip()

        from django.contrib import messages
        if price_inr < 0 or per_seat_price_inr < 0 or billing_cycle_days <= 0:
            messages.error(request, "Invalid numeric values. Price/duration must be positive.")
            return redirect("meeting-admin-plans-create")

        # Create MeetingPlan
        plan = MeetingPlan.objects.create(
            name=name, code=code, description=description, plan_type=plan_type,
            price_inr=price_inr, per_seat_price_inr=per_seat_price_inr,
            billing_cycle_days=billing_cycle_days, max_participants=max_participants,
            max_duration_minutes=max_duration_minutes, allow_cloud_recording=allow_cloud_recording,
            allow_screen_share=allow_screen_share, allow_captions=allow_captions,
            allow_developer_api=allow_developer_api, max_api_calls_per_day=max_api_calls_per_day,
            max_concurrent_rooms=max_concurrent_rooms, storage_limit_mb=storage_limit_mb,
            is_active=is_active, visibility=visibility, is_popular=is_popular, badge_text=badge_text
        )
        
        # Log to Audit Log
        from pms.models import BillingAuditLog
        BillingAuditLog.objects.create(
            event_type="plan_change",
            description=f"Created new plan '{plan.name}' ({plan.code}) dynamically.",
            performed_by=request.user
        )
        messages.success(request, f"Plan '{plan.name}' created successfully!")
        return redirect("meeting-admin-plans")

    return render(request, "subscription/admin_plan_form.html", {"action": "create"})


@login_required
def admin_plan_edit(request, plan_id):
    _require_admin(request)
    plan = get_object_or_404(MeetingPlan, id=plan_id)
    if request.method == "POST":
        plan.name = request.POST.get("name", "").strip()
        plan.description = request.POST.get("description", "").strip()
        plan.plan_type = request.POST.get("plan_type", "free").strip()
        plan.price_inr = Decimal(request.POST.get("price_inr", "0.00"))
        plan.per_seat_price_inr = Decimal(request.POST.get("per_seat_price_inr", "0.00"))
        plan.billing_cycle_days = int(request.POST.get("billing_cycle_days", 30))
        plan.max_participants = int(request.POST.get("max_participants", 2))
        plan.max_duration_minutes = int(request.POST.get("max_duration_minutes", 40))
        plan.allow_cloud_recording = "allow_cloud_recording" in request.POST
        plan.allow_screen_share = "allow_screen_share" in request.POST
        plan.allow_captions = "allow_captions" in request.POST
        plan.allow_developer_api = "allow_developer_api" in request.POST
        plan.max_api_calls_per_day = int(request.POST.get("max_api_calls_per_day", 100))
        plan.max_concurrent_rooms = int(request.POST.get("max_concurrent_rooms", 1))
        plan.storage_limit_mb = int(request.POST.get("storage_limit_mb", 0))
        plan.is_active = "is_active" in request.POST
        plan.visibility = request.POST.get("visibility", "public").strip()
        plan.is_popular = "is_popular" in request.POST
        plan.badge_text = request.POST.get("badge_text", "").strip()
        plan.save()

        from django.contrib import messages
        from pms.models import BillingAuditLog
        BillingAuditLog.objects.create(
            event_type="plan_change",
            description=f"Edited plan '{plan.name}' ({plan.code}).",
            performed_by=request.user
        )
        messages.success(request, f"Plan '{plan.name}' updated successfully!")
        return redirect("meeting-admin-plans")

    return render(request, "subscription/admin_plan_form.html", {"plan": plan, "action": "edit"})


@login_required
def admin_plan_archive(request, plan_id):
    _require_admin(request)
    if request.method == "POST":
        plan = get_object_or_404(MeetingPlan, id=plan_id)
        plan.is_archived = True
        plan.is_active = False
        plan.save()

        from django.contrib import messages
        from pms.models import BillingAuditLog
        BillingAuditLog.objects.create(
            event_type="plan_change",
            description=f"Archived plan '{plan.name}' ({plan.code}).",
            performed_by=request.user
        )
        messages.success(request, f"Plan '{plan.name}' archived successfully.")
    return redirect("meeting-admin-plans")


@login_required
def admin_plan_toggle(request, plan_id):
    _require_admin(request)
    if request.method == "POST":
        plan = get_object_or_404(MeetingPlan, id=plan_id)
        plan.is_active = not plan.is_active
        plan.save()
        status_str = "activated" if plan.is_active else "deactivated"
        from django.contrib import messages
        messages.success(request, f"Plan '{plan.name}' has been {status_str}.")
    return redirect("meeting-admin-plans")


@login_required
def admin_gateway_list(request):
    _require_admin(request)
    seed_default_gateways_if_empty()
    from pms.models import PaymentGateway
    gateways = PaymentGateway.objects.all().order_by("priority", "id")
    return render(request, "subscription/admin_gateways.html", {"gateways": gateways})


@login_required
def admin_gateway_edit(request, gateway_id):
    _require_admin(request)
    from pms.models import PaymentGateway, BillingAuditLog
    from django.contrib import messages
    gateway = get_object_or_404(PaymentGateway, id=gateway_id)

    if request.method == "POST":
        gateway.display_name = request.POST.get("display_name", "").strip()
        gateway.is_enabled = "is_enabled" in request.POST
        gateway.priority = int(request.POST.get("priority", 0))
        gateway.is_live = "is_live" in request.POST

        key_id = request.POST.get("api_key_id", "").strip()
        secret = request.POST.get("api_secret", "").strip()
        if key_id:
            gateway.api_key_id = key_id
        if secret:
            gateway.api_secret = secret

        if gateway.name == "phonepe":
            gateway.phonepe_salt_index = request.POST.get("phonepe_salt_index", "1").strip()
            gateway.phonepe_env = request.POST.get("phonepe_env", "UAT")

        gateway.save()

        is_default_flag = "is_default" in request.POST
        if is_default_flag:
            gateway.is_default = True
            gateway.save()

        BillingAuditLog.objects.create(
            event_type="gateway_change",
            description=f"Updated payment gateway '{gateway.display_name}' configuration.",
            performed_by=request.user
        )
        messages.success(request, f"Gateway '{gateway.display_name}' configured successfully.")
        return redirect("meeting-admin-gateways")

    masked_key = f"...{gateway.api_key_id[-6:]}" if len(gateway.api_key_id) > 6 else ""
    return render(request, "subscription/admin_gateway_form.html", {
        "gateway": gateway,
        "masked_key": masked_key,
    })


@login_required
def admin_billing_dashboard(request):
    _require_admin(request)
    from pms.models import UserSubscription, CustomOffer, ManualAccessGrant, BillingAuditLog, Organization
    subscriptions = UserSubscription.objects.all().select_related("user", "plan", "organization").order_by("-start_date")
    custom_offers = CustomOffer.objects.all().select_related("organization", "plan")
    manual_grants = ManualAccessGrant.objects.all().select_related("user", "organization", "plan", "granted_by")
    audit_logs = BillingAuditLog.objects.all().select_related("performed_by")[:100]

    organizations = Organization.objects.all()
    plans = MeetingPlan.objects.filter(is_active=True, is_archived=False)

    context = {
        "subscriptions": subscriptions,
        "custom_offers": custom_offers,
        "manual_grants": manual_grants,
        "audit_logs": audit_logs,
        "organizations": organizations,
        "plans": plans,
    }
    return render(request, "subscription/admin_billing.html", context)


@login_required
def admin_custom_offer(request):
    _require_admin(request)
    from pms.models import CustomOffer, CustomOfferAuditLog, BillingAuditLog, Organization
    from django.contrib import messages

    if request.method == "POST":
        org_id = request.POST.get("organization_id")
        plan_id = request.POST.get("plan_id")
        price_override = Decimal(request.POST.get("price_override", "0.00"))
        reason = request.POST.get("reason", "").strip()

        org = get_object_or_404(Organization, id=org_id)
        plan = get_object_or_404(MeetingPlan, id=plan_id)

        if price_override < 0:
            messages.error(request, "Override price must be positive.")
            return redirect("meeting-admin-billing")

        old_offer = CustomOffer.objects.filter(organization=org, plan=plan).first()
        old_price = old_offer.price_override if old_offer else None

        offer, created = CustomOffer.objects.update_or_create(
            organization=org, plan=plan,
            defaults={
                "price_override": price_override,
                "reason": reason,
                "created_by": request.user,
                "is_active": True,
            }
        )

        action = "create" if created else "update"
        CustomOfferAuditLog.objects.create(
            organization=org, plan=plan, action=action,
            old_price=old_price, new_price=price_override,
            performed_by=request.user, notes=reason
        )

        BillingAuditLog.objects.create(
            event_type="custom_offer_change",
            description=f"Set custom offer for {org.name} on {plan.name}: ₹{price_override}.",
            performed_by=request.user
        )

        messages.success(request, f"Custom offer for '{org.name}' successfully configured!")

    return redirect("meeting-admin-billing")


@login_required
def admin_manual_grant(request):
    _require_admin(request)
    from pms.models import UserSubscription, ManualAccessGrant, BillingAuditLog, Organization
    from django.contrib import messages
    from django.contrib.auth.models import User

    if request.method == "POST":
        org_id = request.POST.get("organization_id")
        plan_id = request.POST.get("plan_id")
        username = request.POST.get("username", "").strip()
        reason = request.POST.get("reason", "").strip()
        duration_days = int(request.POST.get("duration_days", 30))

        org = get_object_or_404(Organization, id=org_id)
        plan = get_object_or_404(MeetingPlan, id=plan_id)
        target_user = get_object_or_404(User, username=username)

        grant = ManualAccessGrant.objects.create(
            user=target_user, organization=org, plan=plan,
            granted_by=request.user, reason=reason,
            start_date=timezone.now(),
            expiry_date=timezone.now() + timedelta(days=duration_days)
        )

        UserSubscription.objects.filter(organization=org, status="active").update(status="cancelled")

        UserSubscription.objects.create(
            user=target_user,
            organization=org,
            plan=plan,
            api_calls_limit=plan.max_api_calls_per_day,
            rooms_limit=plan.max_concurrent_rooms,
            storage_limit_mb=plan.storage_limit_mb,
            status="active",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=duration_days),
            payment_gateway="manual",
            external_subscription_id=f"MANUAL_GRANT_{grant.id}",
        )

        BillingAuditLog.objects.create(
            event_type="manual_grant",
            description=f"Granted manual access to organization '{org.name}' for plan '{plan.name}' by admin '{request.user.username}' for {duration_days} days. Reason: {reason}",
            performed_by=request.user
        )

        messages.success(request, f"Manual access granted to '{org.name}' successfully!")

    return redirect("meeting-admin-billing")


def _require_admin(request):
    from django.core.exceptions import PermissionDenied
    if not request.user.is_superuser and not request.user.is_staff:
        raise PermissionDenied("Only authorized staff and superusers can access this section.")
