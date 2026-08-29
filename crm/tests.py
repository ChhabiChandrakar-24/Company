from django.test import TestCase, Client
from django.contrib.auth.models import User, Permission
from employee.models import Employee, EmployeeWorkInformation
from base.models import Company, Department, JobPosition
from crm.models import (
    CRMClient, Inquiry, ClientRequirement, Quotation, 
    CRMProjectLink, CRMMeetingLink, CRMCommunication, 
    ClientPayment, CRMActivityLog
)
from project.models import Project
from pms.models import Meetings

class CRMClientLifecycleTests(TestCase):
    def _create_user_with_employee(self, username, email, is_superuser=False):
        if is_superuser:
            user = User.objects.create_superuser(username=username, email=email, password="Password123!")
        else:
            user = User.objects.create_user(username=username, email=email, password="Password123!")
        user.is_new_employee = False
        user.save()
        
        emp = Employee(
            employee_user_id=user,
            employee_first_name=username.capitalize(),
            employee_last_name="Test",
            email=email,
        )
        emp.save()
        
        # Get automatically created work info and configure
        work_info = emp.employee_work_info
        work_info.company_id = self.company
        work_info.department_id = self.dept
        work_info.job_position_id = self.job_pos
        work_info.save()
        return user, emp

    def setUp(self):
        # Clear thread request locals
        from chhabi.chhabi_middlewares import _thread_locals
        if hasattr(_thread_locals, "request"):
            del _thread_locals.request

        # Setup base models
        self.company = Company(company="Geeta Forgetech")
        self.company.save()
        
        self.dept = Department(department="Engineering")
        self.dept.save()
        
        self.job_pos = JobPosition(job_position="Software Engineer", department_id=self.dept)
        self.job_pos.save()

        # Mock request for project save
        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser
        factory = RequestFactory()
        req = factory.get('/')
        req.session = {"selected_company": "all"}
        req.user = AnonymousUser()
        _thread_locals.request = req

        # Create admin and regular employee
        self.admin_user, self.admin_emp = self._create_user_with_employee("adminhr", "admin@example.com", is_superuser=True)
        self.emp_user, self.emp_emp = self._create_user_with_employee("devuser", "dev@example.com", is_superuser=False)
        self.client = Client()

    def test_01_inquiry_creation_and_duplicate_prevention(self):
        """Test that client records are reused and not duplicated across inquiries."""
        self.client.force_login(self.admin_user)

        # 1. Post a new inquiry for John Doe
        inquiry_data_1 = {
            "client_name": "John Doe",
            "company_name": "JD Enterprises",
            "email": "johndoe@example.com",
            "phone": "9876543210",
            "source": "Website",
            "interested_service": "Cloud Migration",
            "initial_requirement": "Migrate core systems to GCP.",
            "assignee": self.admin_emp.id,
            "status": "inquiry",
        }
        resp = self.client.post("/crm/inquiries/create/", data=inquiry_data_1)
        self.assertEqual(resp.status_code, 302) # Redirects to list on success

        # Verify client and inquiry creation
        self.assertEqual(CRMClient.objects.count(), 1)
        self.assertEqual(Inquiry.objects.count(), 1)
        
        client_record = CRMClient.objects.first()
        self.assertEqual(client_record.name, "John Doe")
        self.assertEqual(client_record.email, "johndoe@example.com")
        self.assertEqual(client_record.status, "lead")

        # Verify activity log creation
        logs = CRMActivityLog.objects.filter(client=client_record)
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs[0].activity_type, "inquiry")

        # 2. Post a SECOND inquiry with the SAME email, but different details
        inquiry_data_2 = {
            "client_name": "John Doe",
            "company_name": "JD Global Corp", # Updated company
            "email": "johndoe@example.com",  # Same email
            "phone": "9876543211",           # Updated phone
            "source": "Referral",
            "interested_service": "Data Engineering",
            "initial_requirement": "Setup BigQuery data warehouse.",
            "assignee": self.admin_emp.id,
            "status": "lead",
        }
        resp = self.client.post("/crm/inquiries/create/", data=inquiry_data_2)
        self.assertEqual(resp.status_code, 302)

        # Client count must still be 1 (reused existing record, prevented duplicate!)
        self.assertEqual(CRMClient.objects.count(), 1)
        # Inquiry count must be 2 (history preserved!)
        self.assertEqual(Inquiry.objects.count(), 2)

        client_record.refresh_from_db()
        self.assertEqual(client_record.company_name, "JD Global Corp") # Updated successfully
        self.assertEqual(client_record.phone, "9876543211")

    def test_02_client_conversion_and_lifecycle(self):
        """Test status transitions, automatic status upgrades, and activity logging."""
        self.client.force_login(self.admin_user)

        # 1. Create client and inquiry
        client_obj = CRMClient(name="Alice", email="alice@example.com", status="lead")
        client_obj.save()
        inquiry = Inquiry(client=client_obj, interested_service="DevOps", status="inquiry")
        inquiry.save()

        # 2. Progress status to "confirmed_client"
        update_data = {
            "status": "confirmed_client",
        }
        resp = self.client.post(f"/crm/inquiries/{inquiry.id}/update-status/", data=update_data)
        self.assertEqual(resp.status_code, 302)

        # Check client promotion to permanent/confirmed client record
        client_obj.refresh_from_db()
        self.assertEqual(client_obj.status, "confirmed")

        # Verify activity logs for status transition
        logs = CRMActivityLog.objects.filter(inquiry=inquiry, activity_type="status_change")
        self.assertEqual(logs.count(), 1)
        self.assertIn("from 'Inquiry' to 'Confirmed Client'", logs[0].description)

    def test_03_client_timeline_history(self):
        """Test chronological history timeline rendering for requirements, meetings, quotes, payments, projects, and communications."""
        self.client.force_login(self.admin_user)

        # Setup Client, Inquiry and linked project/meeting
        client_obj = CRMClient(name="Bob", email="bob@example.com", status="lead")
        client_obj.save()
        inquiry = Inquiry(client=client_obj, interested_service="App Development", status="confirmed_client")
        inquiry.save()

        project = Project(title="Bob's Portal", start_date="2026-08-27")
        project.save()

        from django.utils import timezone
        meeting = Meetings(title="Discovery Workshop", date=timezone.now(), end_date=timezone.now() + timezone.timedelta(hours=1))
        meeting.save()

        # 1. Add Requirement
        resp = self.client.post(f"/crm/inquiries/{inquiry.id}/add-requirement/", data={
            "title": "Mobile App UI",
            "description": "Needs dark mode and simple navigation."
        })
        self.assertEqual(resp.status_code, 302)

        # 2. Add Quotation
        resp = self.client.post(f"/crm/inquiries/{inquiry.id}/add-quotation/", data={
            "quote_number": "Q-2026-001",
            "amount": "50000.00",
            "description": "50% advance, 50% on completion",
            "status": "draft"
        })
        self.assertEqual(resp.status_code, 302)

        # 3. Link Project
        resp = self.client.post(f"/crm/inquiries/{inquiry.id}/link-project/", data={
            "project": project.id
        })
        self.assertEqual(resp.status_code, 302)

        # 4. Link Meeting
        resp = self.client.post(f"/crm/inquiries/{inquiry.id}/link-meeting/", data={
            "meeting": meeting.id
        })
        self.assertEqual(resp.status_code, 302)

        # 5. Log Payment
        resp = self.client.post(f"/crm/inquiries/{inquiry.id}/add-payment/", data={
            "amount": "25000.00",
            "payment_date": "2026-08-27",
            "status": "completed",
            "reference_number": "TXN98765"
        })
        self.assertEqual(resp.status_code, 302)

        # 6. Log Communication Note
        resp = self.client.post(f"/crm/inquiries/{inquiry.id}/add-communication/", data={
            "channel": "whatsapp",
            "message": "Bob confirmed receipt of mockups via WhatsApp."
        })
        self.assertEqual(resp.status_code, 302)

        # Verify all activity logs exist in chronological timeline
        logs = CRMActivityLog.objects.filter(client=client_obj).order_by("created_at")
        
        # We expect logs for: requirement, quotation, project, meeting, payment, communication
        types = [log.activity_type for log in logs]
        self.assertIn("requirement", types)
        self.assertIn("quotation", types)
        self.assertIn("project", types)
        self.assertIn("meeting", types)
        self.assertIn("payment", types)
        self.assertIn("communication", types)

        # Verify timeline page loads without error
        timeline_url = f"/crm/clients/{client_obj.id}/timeline/"
        resp = self.client.get(timeline_url)
        self.assertEqual(resp.status_code, 200)

    def test_04_permission_enforcement(self):
        """Verify that employees without proper permissions cannot access CRM dashboards/actions."""
        self.client.force_login(self.emp_user)

        # Pipeline view should be blocked (403 Forbidden)
        resp = self.client.get("/crm/inquiries/")
        self.assertEqual(resp.status_code, 403)

    def test_05_requirement_management_and_revisions(self):
        """Test creating requirements, tracking specification revisions, and posting comments."""
        self.client.force_login(self.admin_user)

        client_obj = CRMClient(name="Charlie", email="charlie@example.com", status="lead")
        client_obj.save()
        inquiry = Inquiry(client=client_obj, interested_service="API Integration", status="requirement_discovery")
        inquiry.save()

        # 1. Create requirement spec
        req_data = {
            "title": "Stripe Payments integration",
            "description": "Integration of Stripe checkout session API.",
            "modules_requested": "Auth, Billing, Webhooks",
            "priority": "high",
            "approval_status": "pending",
        }
        resp = self.client.post(f"/crm/inquiries/{inquiry.id}/requirements/create/", data=req_data)
        self.assertEqual(resp.status_code, 302)

        req = ClientRequirement.objects.first()
        self.assertIsNotNone(req)
        self.assertEqual(req.title, "Stripe Payments integration")
        self.assertEqual(req.revision_number, 1)

        # 2. Edit requirement spec to log revision
        edit_data = {
            "title": "Stripe Payments integration",
            "description": "UPDATED: Integrate Apple Pay too.",
            "modules_requested": "Auth, Billing, Webhooks, ApplePay",
            "priority": "critical",
            "approval_status": "pending",
        }
        resp = self.client.post(f"/crm/requirements/{req.id}/edit/", data=edit_data)
        self.assertEqual(resp.status_code, 302)

        req.refresh_from_db()
        self.assertEqual(req.revision_number, 2)
        self.assertEqual(req.priority, "critical")

        # Check revision record
        revisions = req.revisions.all()
        self.assertEqual(revisions.count(), 1)
        self.assertEqual(revisions[0].revision_number, 1)
        self.assertEqual(revisions[0].description, "Integration of Stripe checkout session API.")

        # 3. Add requirement discussion comment
        comment_data = {
            "comment": "Client requested to support Apple Pay in this revision."
        }
        resp = self.client.post(f"/crm/requirements/{req.id}/comment/", data=comment_data)
        self.assertEqual(resp.status_code, 302)

        comments = req.comments.all()
        self.assertEqual(comments.count(), 1)
        self.assertEqual(comments[0].comment, "Client requested to support Apple Pay in this revision.")
        self.assertEqual(comments[0].author, self.admin_user)

    def test_06_client_scheduler(self):
        """Test scheduling client meetings via scheduler integration."""
        self.client.force_login(self.admin_user)

        client_obj = CRMClient(name="David", email="david@example.com", status="lead")
        client_obj.save()
        inquiry = Inquiry(client=client_obj, interested_service="Consultation", status="inquiry")
        inquiry.save()

        # Schedule meeting
        meeting_data = {
            "title": "Discovery Workshop Call",
            "date": "2026-08-27T14:00",
            "end_date": "2026-08-27T15:00",
            "description": "Initial requirement alignment call.",
            "meeting_type": "external",
            "provider": "google_meet",
            "employee_id": [self.admin_emp.id],
        }
        resp = self.client.post(f"/crm/inquiries/{inquiry.id}/schedule-meeting/", data=meeting_data)
        self.assertEqual(resp.status_code, 302)

        # Check meeting is created in PMS
        meeting = Meetings.objects.first()
        self.assertIsNotNone(meeting)
        self.assertEqual(meeting.title, "Discovery Workshop Call")
        self.assertEqual(meeting.meeting_type, "external")

        # Check CRM link and activity log
        self.assertTrue(CRMMeetingLink.objects.filter(inquiry=inquiry, meeting=meeting).exists())
        self.assertTrue(CRMActivityLog.objects.filter(inquiry=inquiry, activity_type="meeting").exists())

    def test_07_one_click_portal_access_and_revocation(self):
        """Test secure revocable portal access setup, token validation, and revoking client access."""
        self.client.force_login(self.admin_user)

        client_obj = CRMClient(name="Emily", email="emily@example.com", status="lead")
        client_obj.save()
        inquiry = Inquiry(client=client_obj, interested_service="Platform setup", status="confirmed_client")
        inquiry.save()

        # 1. Grant Access
        resp = self.client.get(f"/crm/clients/{client_obj.id}/access/grant/")
        self.assertEqual(resp.status_code, 302)

        client_obj.refresh_from_db()
        self.assertTrue(client_obj.is_portal_active)
        self.assertIsNotNone(client_obj.portal_user)
        self.assertTrue(client_obj.portal_user.is_active)

        # Extract setup token link from session
        setup_link = self.client.session.get("portal_setup_link")
        self.assertIsNotNone(setup_link)

        # 2. Token Login
        self.client.logout()
        # Parse path from absolute link
        path_start = setup_link.find("/crm/portal/login/")
        login_path = setup_link[path_start:]
        
        resp = self.client.get(login_path)
        self.assertEqual(resp.status_code, 302) # Logs in and redirects to portal dashboard
        self.assertEqual(resp.url, "/crm/portal/")

        # Verify portal dashboard loads and restricts to correct client
        resp = self.client.get("/crm/portal/")
        if resp.status_code == 302:
            print("--- PORTAL DASHBOARD REDIRECT TARGET:", resp.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Welcome, Emily!")

        # 3. Access Revocation
        self.client.logout()
        self.client.force_login(self.admin_user)
        resp = self.client.get(f"/crm/clients/{client_obj.id}/access/revoke/")
        self.assertEqual(resp.status_code, 302)

        client_obj.refresh_from_db()
        self.assertFalse(client_obj.is_portal_active)
        self.assertFalse(client_obj.portal_user.is_active)

        # Attempt token login after revocation
        self.client.logout()
        resp = self.client.get(login_path)
        # Verify it refuses authentication and redirects to login with error
        self.assertEqual(resp.status_code, 302)
        self.assertNotEqual(resp.url, "/crm/portal/")

