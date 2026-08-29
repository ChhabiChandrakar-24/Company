import json
import secrets
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.utils import timezone

from pms.models import (
    Meetings,
    MeetingPlan,
    UserSubscription,
    PaymentTransaction,
    DeveloperApiKey,
    MeetingGuestToken,
    PaymentGatewayConfig,
)
from pms.payment_gateways import RazorpayGateway, PhonePeGateway
from pms.subscription_views import seed_default_plans_if_empty


class MeetingSubscriptionAndDeveloperApiTests(TestCase):
    def _create_user_with_employee(self, username, email, is_superuser=False):
        if is_superuser:
            user = User.objects.create_superuser(username=username, email=email, password="Password123!")
        else:
            user = User.objects.create_user(username=username, email=email, password="Password123!")
        user.is_new_employee = False
        user.save()
        from employee.models import Employee
        Employee.objects.create(
            employee_user_id=user,
            employee_first_name="Test",
            employee_last_name="User",
            email=email,
        )
        return user

    def setUp(self):
        from chhabi.chhabi_middlewares import _thread_locals
        if hasattr(_thread_locals, "request"):
            del _thread_locals.request

        seed_default_plans_if_empty()

        self.user = self._create_user_with_employee(
            username="testdeveloper",
            email="dev@example.com",
        )
        self.client = Client()

    def tearDown(self):
        from chhabi.chhabi_middlewares import _thread_locals
        if hasattr(_thread_locals, "request"):
            del _thread_locals.request

    def test_01_seed_plans_exist(self):
        """Test default plans (Free, P2P Starter, Pro Monthly, Enterprise) are created."""
        plans = MeetingPlan.objects.all()
        self.assertGreaterEqual(plans.count(), 4)

        free_plan = MeetingPlan.objects.get(code="free")
        self.assertEqual(free_plan.price_inr, Decimal("0.00"))
        self.assertEqual(free_plan.max_participants, 2)

        p2p_plan = MeetingPlan.objects.get(code="p2p_starter")
        self.assertEqual(p2p_plan.price_inr, Decimal("499.00"))
        self.assertTrue(p2p_plan.allow_developer_api)

        pro_plan = MeetingPlan.objects.get(code="pro_monthly")
        self.assertEqual(pro_plan.price_inr, Decimal("1499.00"))
        self.assertEqual(pro_plan.max_participants, 50)

    def test_02_subscription_creation_and_activation(self):
        """Test subscription activation and expiration date calculation."""
        plan = MeetingPlan.objects.get(code="p2p_starter")
        sub = UserSubscription.objects.create(
            user=self.user,
            plan=plan,
            peer_seats=3,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            status="active",
            payment_gateway="razorpay",
        )
        self.assertTrue(sub.is_currently_active)
        self.assertEqual(sub.peer_seats, 3)

    def test_03_razorpay_order_and_signature_verification(self):
        """Test Razorpay order creation and HMAC-SHA256 signature verification."""
        order = RazorpayGateway.create_order(amount_inr=Decimal("499.00"), receipt_id="RCP_123")
        self.assertTrue(order.get("id"))
        self.assertEqual(order.get("amount"), 49900) # 499 * 100 paise

        # Test signature verification
        is_valid = RazorpayGateway.verify_payment_signature(
            razorpay_order_id=order["id"],
            razorpay_payment_id="pay_sim_12345",
            razorpay_signature="simulated_signature",
        )
        self.assertTrue(is_valid)

    def test_04_phonepe_request_generation(self):
        """Test PhonePe payload generation and checksum verification."""
        res = PhonePeGateway.create_payment_request(
            amount_inr=Decimal("1499.00"),
            transaction_id="TXN_TEST_999",
            user_id=self.user.id,
            redirect_url="http://localhost:8000/pms/subscription/phonepe/callback/",
            callback_url="http://localhost:8000/pms/subscription/phonepe/callback/",
        )
        self.assertTrue(res.get("success"))
        self.assertTrue(res.get("pay_url"))
        self.assertTrue(res.get("x_verify"))

    def test_05_developer_api_key_and_meeting_creation(self):
        """Test Developer REST API creates meeting, returns host and guest URLs with tokens."""
        # Activate Pro plan with Developer API access
        pro_plan = MeetingPlan.objects.get(code="pro_monthly")
        sub = UserSubscription.objects.create(
            user=self.user,
            plan=pro_plan,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            status="active",
        )

        api_key = f"hrz_test_{secrets.token_hex(16)}"
        api_secret = f"sec_test_{secrets.token_urlsafe(32)}"
        app_key = DeveloperApiKey.objects.create(
            user=self.user,
            subscription=sub,
            app_name="Telehealth App",
            api_key=api_key,
            api_secret=api_secret,
        )

        # Call POST /pms/api/v1/meetings/create/
        payload = {
            "title": "Dr. Consultation Room",
            "host_name": "Dr. Ramesh (Cardiologist)",
            "guest_name": "Amit Kumar (Patient)",
            "allow_recording": True,
            "allow_chat": True,
            "allow_captions": True,
        }
        resp = self.client.post(
            "/pms/api/v1/meetings/create/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=api_key,
            HTTP_X_API_SECRET=api_secret,
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()

        self.assertEqual(data["status"], "success")
        self.assertTrue(data.get("meeting_id"))
        self.assertIn("join_url_host", data)
        self.assertIn("join_url_participant", data)
        self.assertTrue(data.get("host_token"))
        self.assertTrue(data.get("participant_token"))

        meeting_id = data["meeting_id"]

        # Call GET /pms/api/v1/meetings/<id>/
        get_resp = self.client.get(
            f"/pms/api/v1/meetings/{meeting_id}/",
            HTTP_X_API_KEY=api_key,
        )
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["id"], meeting_id)

        # Call POST /pms/api/v1/meetings/<id>/join-token/ to create 3rd attendee link
        join_resp = self.client.post(
            f"/pms/api/v1/meetings/{meeting_id}/join-token/",
            data=json.dumps({"guest_name": "Nurse Sunita", "guest_role": "participant"}),
            content_type="application/json",
            HTTP_X_API_KEY=api_key,
        )
        self.assertEqual(join_resp.status_code, 200)
        join_data = join_resp.json()
        self.assertEqual(join_data["guest_name"], "Nurse Sunita")
        self.assertIn("token", join_data)

        # Call GET /pms/api/v1/developer/usage/
        usage_resp = self.client.get(
            "/pms/api/v1/developer/usage/",
            HTTP_X_API_KEY=api_key,
        )
        self.assertEqual(usage_resp.status_code, 200)
        usage_data = usage_resp.json()
        self.assertGreaterEqual(usage_data["total_requests"], 3)

    def test_06_guest_token_video_room_access(self):
        """Test that an external guest with a signed token can access the video call room without login."""
        meeting = Meetings.objects.create(
            title="External Guest Interview",
            date=timezone.now(),
            end_date=timezone.now() + timedelta(hours=1),
            meeting_type="internal",
            provider="internal",
        )
        token_str = f"gt_test_{secrets.token_hex(16)}"
        guest_token = MeetingGuestToken.objects.create(
            meeting=meeting,
            token=token_str,
            guest_name="Client Guest User",
            guest_role="participant",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Client is not logged in
        resp = self.client.get(f"/pms/meeting-call/{meeting.room_code}/?token={token_str}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Client Guest User")

        # Test guest posting message
        msg_resp = self.client.post(
            f"/pms/meeting-call/{meeting.room_code}/message/?token={token_str}",
            data={"message": "Hello from external guest!"},
        )
        self.assertEqual(msg_resp.status_code, 201)
        self.assertEqual(msg_resp.json()["sender"], "Client Guest User")

    def test_07_tenant_isolation_meetings_and_dashboard(self):
        """Test multi-organization tenant data isolation and metrics dashboard access."""
        from pms.models import Organization, OrganizationMember

        from employee.models import Employee

        # Create Org A and User A
        org_a = Organization.objects.create(name="Org A", slug="org-a")
        user_a = User.objects.create_user(username="usera", email="usera@example.com", password="Password123!")
        user_a.is_new_employee = False
        user_a.save()
        Employee.objects.create(
            employee_user_id=user_a,
            employee_first_name="User",
            employee_last_name="A",
            email="usera@example.com",
        )
        OrganizationMember.objects.create(organization=org_a, user=user_a, role="owner")

        # Create Org B and User B
        org_b = Organization.objects.create(name="Org B", slug="org-b")
        user_b = User.objects.create_user(username="userb", email="userb@example.com", password="Password123!")
        user_b.is_new_employee = False
        user_b.save()
        Employee.objects.create(
            employee_user_id=user_b,
            employee_first_name="User",
            employee_last_name="B",
            email="userb@example.com",
        )
        OrganizationMember.objects.create(organization=org_b, user=user_b, role="owner")

        # Setup pro subscription plan
        plan = MeetingPlan.objects.get(code="pro_monthly")

        # Create User subscriptions for Org A and Org B
        sub_a = UserSubscription.objects.create(
            user=user_a,
            organization=org_a,
            plan=plan,
            api_calls_limit=10,
            rooms_limit=2,
            status="active",
            end_date=timezone.now() + timedelta(days=30),
        )

        sub_b = UserSubscription.objects.create(
            user=user_b,
            organization=org_b,
            plan=plan,
            api_calls_limit=10,
            rooms_limit=2,
            status="active",
            end_date=timezone.now() + timedelta(days=30),
        )

        # Login as User A
        self.client.force_login(user_a)

        # Create Meeting in Org A via API key (with request.organization attached)
        api_key = f"hrz_test_a_{secrets.token_hex(16)}"
        api_secret = f"sec_test_a_{secrets.token_urlsafe(32)}"
        app_key = DeveloperApiKey.objects.create(
            user=user_a,
            subscription=sub_a,
            app_name="App A",
            api_key=api_key,
            api_secret=api_secret,
        )

        payload = {
            "title": "Org A Confidential Meeting",
            "host_name": "Host A",
            "guest_name": "Guest A",
        }
        resp = self.client.post(
            "/pms/api/v1/meetings/create/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=api_key,
            HTTP_X_API_SECRET=api_secret,
        )
        self.assertEqual(resp.status_code, 201)
        meeting_a_id = resp.json()["meeting_id"]

        # User B (different org) attempts to fetch this meeting via developer API (raises 404/403 or filters it out)
        api_key_b = f"hrz_test_b_{secrets.token_hex(16)}"
        api_secret_b = f"sec_test_b_{secrets.token_urlsafe(32)}"
        app_key_b = DeveloperApiKey.objects.create(
            user=user_b,
            subscription=sub_b,
            app_name="App B",
            api_key=api_key_b,
            api_secret=api_secret_b,
        )

        get_resp = self.client.get(
            f"/pms/api/v1/meetings/{meeting_a_id}/",
            HTTP_X_API_KEY=api_key_b,
        )
        # Verify strict isolation: Org B API key must not find or access Org A meeting
        self.assertEqual(get_resp.status_code, 404)

        # Verify Dashboard isolation for User A
        self.client.force_login(user_a)
        dash_a_resp = self.client.get("/pms/saas/dashboard/")
        self.assertEqual(dash_a_resp.status_code, 200)
        self.assertContains(dash_a_resp, "Org A")
        self.assertNotContains(dash_a_resp, "Org B")

        # Verify Dashboard isolation for User B
        self.client.force_login(user_b)
        dash_b_resp = self.client.get("/pms/saas/dashboard/")
        self.assertEqual(dash_b_resp.status_code, 200)
        self.assertContains(dash_b_resp, "Org B")
        self.assertNotContains(dash_b_resp, "Org A")

    def test_08_tenant_quota_limits(self):
        """Test rooms creation daily limit enforcement."""
        from pms.models import Organization, OrganizationMember

        from employee.models import Employee

        org = Organization.objects.create(name="Limit Org", slug="limit-org")
        user = User.objects.create_user(username="limituser", email="limit@example.com", password="Password123!")
        user.is_new_employee = False
        user.save()
        Employee.objects.create(
            employee_user_id=user,
            employee_first_name="Limit",
            employee_last_name="User",
            email="limit@example.com",
        )
        OrganizationMember.objects.create(organization=org, user=user, role="owner")
        
        plan = MeetingPlan.objects.get(code="pro_monthly")
        sub = UserSubscription.objects.create(
            user=user,
            organization=org,
            plan=plan,
            api_calls_limit=10,
            rooms_limit=1,  # Set quota to exactly 1 room per day!
            status="active",
            end_date=timezone.now() + timedelta(days=30),
        )

        api_key = f"hrz_test_{secrets.token_hex(16)}"
        api_secret = f"sec_test_{secrets.token_urlsafe(32)}"
        app_key = DeveloperApiKey.objects.create(
            user=user,
            subscription=sub,
            app_name="Limit App",
            api_key=api_key,
            api_secret=api_secret,
        )

        payload = {"title": "First Meeting"}
        
        # First creation succeeds
        resp1 = self.client.post(
            "/pms/api/v1/meetings/create/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=api_key,
            HTTP_X_API_SECRET=api_secret,
        )
        self.assertEqual(resp1.status_code, 201)

        # Second creation fails with 429 Too Many Requests (Quota Exceeded)
        resp2 = self.client.post(
            "/pms/api/v1/meetings/create/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=api_key,
            HTTP_X_API_SECRET=api_secret,
        )
        self.assertEqual(resp2.status_code, 429)
        self.assertIn("Quota exceeded", resp2.json()["detail"])

    def test_09_dynamic_plan_management_admin(self):
        """Test Super Admin dashboard views for dynamic plan list, create, edit, archive and toggle."""
        # Create Super User
        admin_user = self._create_user_with_employee(username="adminuser", email="admin@example.com", is_superuser=True)
        
        # Test permission restriction (normal user access)
        self.client.force_login(self.user)
        resp = self.client.get("/pms/subscription/admin/plans/")
        self.assertEqual(resp.status_code, 403)

        # Staff login
        self.client.force_login(admin_user)
        
        # Get plans list
        resp = self.client.get("/pms/subscription/admin/plans/")
        self.assertEqual(resp.status_code, 200)

        # Create plan dynamically
        create_data = {
            "name": "Dynamic Gold Plan",
            "code": "dynamic_gold",
            "description": "High tier gold plan",
            "plan_type": "pro_monthly",
            "price_inr": "2500.00",
            "per_seat_price_inr": "150.00",
            "billing_cycle_days": 30,
            "max_participants": 100,
            "max_duration_minutes": 180,
            "max_api_calls_per_day": 2000,
            "max_concurrent_rooms": 10,
            "storage_limit_mb": 5000,
            "is_active": "on",
            "visibility": "public",
            "badge_text": "POPULAR",
        }
        resp = self.client.post("/pms/subscription/admin/plans/create/", data=create_data)
        self.assertEqual(resp.status_code, 302) # Redirect to plans list
        
        plan = MeetingPlan.objects.get(code="dynamic_gold")
        self.assertEqual(plan.name, "Dynamic Gold Plan")
        self.assertEqual(plan.price_inr, Decimal("2500.00"))
        self.assertTrue(plan.is_active)

        # Toggle plan status
        resp = self.client.post(f"/pms/subscription/admin/plans/{plan.id}/toggle/")
        self.assertEqual(resp.status_code, 302)
        plan.refresh_from_db()
        self.assertFalse(plan.is_active)

        # Archive plan
        resp = self.client.post(f"/pms/subscription/admin/plans/{plan.id}/archive/")
        self.assertEqual(resp.status_code, 302)
        plan.refresh_from_db()
        self.assertTrue(plan.is_archived)

    def test_10_payment_gateway_admin_and_default(self):
        """Test payment gateway list, configuration, and default constraint enforcement (only one default)."""
        admin_user = self._create_user_with_employee(username="adminuser2", email="admin2@example.com", is_superuser=True)
        self.client.force_login(admin_user)

        from pms.models import PaymentGateway
        # Gateway list page triggers seeding if empty
        resp = self.client.get("/pms/subscription/admin/gateways/")
        self.assertEqual(resp.status_code, 200)

        rzp_gateway = PaymentGateway.objects.get(name="razorpay")
        phonepe_gateway = PaymentGateway.objects.get(name="phonepe")

        # By default, Razorpay is default. Let's make PhonePe the default gateway
        self.assertTrue(rzp_gateway.is_default)
        self.assertFalse(phonepe_gateway.is_default)

        # Edit PhonePe configuration to make it default
        edit_data = {
            "display_name": "PhonePe UPI",
            "is_enabled": "on",
            "priority": 1,
            "is_default": "on",
            "api_key_id": "MERCHANT_XYZ",
            "api_secret": "SALT_SECRET_XYZ",
            "phonepe_salt_index": "2",
            "phonepe_env": "PROD",
        }
        resp = self.client.post(f"/pms/subscription/admin/gateways/{phonepe_gateway.id}/edit/", data=edit_data)
        self.assertEqual(resp.status_code, 302)

        phonepe_gateway.refresh_from_db()
        rzp_gateway.refresh_from_db()

        # Verify only PhonePe is default now (Razorpay should be set to is_default=False automatically)
        self.assertTrue(phonepe_gateway.is_default)
        self.assertFalse(rzp_gateway.is_default)

    def test_11_custom_pricing_checkout(self):
        """Test custom organization offers overriding plan pricing for checkout orders."""
        from pms.models import Organization, OrganizationMember, CustomOffer
        from employee.models import Employee

        org = Organization.objects.create(name="Custom Org", slug="custom-org")
        OrganizationMember.objects.create(organization=org, user=self.user, role="admin")

        admin_user = self._create_user_with_employee(username="adminuser3", email="admin3@example.com", is_superuser=True)
        self.client.force_login(admin_user)

        plan = MeetingPlan.objects.get(code="pro_monthly") # standard price ₹1499

        # Add custom offer of ₹999 for this organization
        custom_offer_data = {
            "organization_id": org.id,
            "plan_id": plan.id,
            "price_override": "999.00",
            "reason": "Special discount offer",
        }
        resp = self.client.post("/pms/subscription/admin/billing/custom-offer/", data=custom_offer_data)
        self.assertEqual(resp.status_code, 302)

        offer = CustomOffer.objects.get(organization=org, plan=plan)
        self.assertEqual(offer.price_override, Decimal("999.00"))

        # Now login back as normal developer user
        self.client.force_login(self.user)

        # Mocking organization tenant scope on request
        session = self.client.session
        session["selected_company"] = org.id
        session.save()

        # Fetch plans list and verify override is rendered
        resp = self.client.get("/pms/subscription/plans/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "999") # Price override should be shown

        # Create checkout order and check transaction amount is ₹999 instead of ₹1499
        order_data = {
            "plan_id": plan.id,
            "gateway": "razorpay",
            "peer_seats": 1,
        }
        # In django test client, we pass JSON payload
        resp_order = self.client.post(
            "/pms/subscription/checkout/order/",
            data=json.dumps(order_data),
            content_type="application/json",
        )
        self.assertEqual(resp_order.status_code, 200)
        order_json = resp_order.json()
        self.assertEqual(order_json["status"], "success")

        # Razorpay amount should be 999 * 100 paise = 99900
        self.assertEqual(order_json["amount_paise"], 99900)

        # Payment Transaction record should be ₹999.00
        txn = PaymentTransaction.objects.get(order_id=order_json["order_id"])
        self.assertEqual(txn.amount, Decimal("999.00"))

    def test_12_manual_access_grant(self):
        """Test manually assigning subscription access, deactivating older plans, and audit logging."""
        from pms.models import Organization, OrganizationMember, ManualAccessGrant, UserSubscription
        org = Organization.objects.create(name="Manual Org", slug="manual-org")
        OrganizationMember.objects.create(organization=org, user=self.user, role="owner")

        # Start with an active standard subscription
        plan_old = MeetingPlan.objects.get(code="free")
        UserSubscription.objects.create(
            user=self.user,
            organization=org,
            plan=plan_old,
            status="active",
        )

        admin_user = self._create_user_with_employee(username="adminuser4", email="admin4@example.com", is_superuser=True)
        self.client.force_login(admin_user)

        plan_new = MeetingPlan.objects.get(code="pro_monthly")

        # Assign manual complimentary access for 60 days
        grant_data = {
            "organization_id": org.id,
            "plan_id": plan_new.id,
            "username": self.user.username,
            "reason": "Promotional partnership access",
            "duration_days": 60,
        }
        resp = self.client.post("/pms/subscription/admin/billing/manual-grant/", data=grant_data)
        self.assertEqual(resp.status_code, 302)

        # Old subscription must be cancelled
        old_subs = UserSubscription.objects.filter(organization=org, plan=plan_old)
        for s in old_subs:
            self.assertEqual(s.status, "cancelled")

        # New subscription must be active and set correctly
        new_sub = UserSubscription.objects.filter(organization=org, plan=plan_new, status="active").first()
        self.assertIsNotNone(new_sub)
        self.assertEqual(new_sub.payment_gateway, "manual")

        # Manual grant log must exist
        grant = ManualAccessGrant.objects.filter(organization=org, user=self.user).first()
        self.assertIsNotNone(grant)
        self.assertEqual(grant.reason, "Promotional partnership access")
        self.assertEqual(grant.granted_by, admin_user)


