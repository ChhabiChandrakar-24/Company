from django.test import TestCase, Client
from django.contrib.auth.models import User
from employee.models import Employee, EmployeeWorkInformation, JoiningLetterTemplate, IssuedJoiningLetter
from offboarding.models import TerminationWorkflow
from base.models import Company, Department, JobPosition
from chhabi_documents.models import Document
from django.urls import reverse

class EmployeeLifecycleTests(TestCase):
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
        
        # Get the automatically created work info and update it
        work_info = emp.employee_work_info
        work_info.company_id = self.company
        work_info.department_id = self.dept
        work_info.job_position_id = self.job_pos
        work_info.save()
        return user, emp

    def setUp(self):
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

        # Create admin and regular employee
        self.admin_user, self.admin_emp = self._create_user_with_employee("adminhr", "admin@example.com", is_superuser=True)
        self.emp_user, self.emp_emp = self._create_user_with_employee("devuser", "dev@example.com", is_superuser=False)
        self.client = Client()

    def test_01_probation_status(self):
        """Test probation status management on EmployeeWorkInformation."""
        work_info = self.emp_emp.employee_work_info
        # Initially defaults to "none"
        self.assertEqual(work_info.probation_status, "none")

        # Set to on probation
        work_info.probation_status = "on_probation"
        work_info.save()
        work_info.refresh_from_db()
        self.assertEqual(work_info.probation_status, "on_probation")

    def test_02_joining_letter_workflow(self):
        """Test template creation, rendering, issuing, and employee action flow."""
        self.client.force_login(self.admin_user)

        # 1. Create Template
        template = JoiningLetterTemplate(
            title="Standard Offer",
            body="Hello {employee_name}, welcome to {company_name} as {designation}.",
            company=self.company,
        )
        template.save()

        # 2. Preview endpoint
        preview_url = f"/employee/joining-letters/preview/?template_id={template.id}&employee_id={self.emp_emp.id}"
        resp = self.client.get(preview_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Hello Devuser Test, welcome to Geeta Forgetech as Software Engineer.", resp.json()["body"])

        # 3. Issue Letter
        issue_data = {
            "employee": self.emp_emp.id,
            "template": template.id,
            "title": "Welcome Offer Letter",
            "body": "",  # let it auto-render
            "status": "issued",
            "issued_date": "2026-08-27",
        }
        resp = self.client.post("/employee/joining-letters/issue/", data=issue_data)
        self.assertEqual(resp.status_code, 302)

        letter = IssuedJoiningLetter.objects.get(employee=self.emp_emp)
        self.assertEqual(letter.status, "issued")
        self.assertIn("welcome to Geeta Forgetech", letter.body)

        # Verification: automatic document creation in chhabi_documents
        doc = Document.objects.filter(employee_id=self.emp_emp).first()
        self.assertIsNotNone(doc)
        self.assertEqual(doc.title, "Welcome Offer Letter")

        # 4. Employee accepts letter
        self.client.force_login(self.emp_user)
        action_url = f"/employee/joining-letters/{letter.id}/action/accept/"
        resp = self.client.post(action_url)
        self.assertEqual(resp.status_code, 302)
        letter.refresh_from_db()
        self.assertEqual(letter.status, "accepted")

    def test_03_termination_and_offboarding_workflow(self):
        """Test initiation, approval, clearance checklist, and deactivation on termination."""
        self.client.force_login(self.admin_user)

        # 1. Initiate Termination
        initiate_data = {
            "employee": self.emp_emp.id,
            "reason": "Redundancy resizing",
            "effective_date": "2026-09-01",
            "termination_letter": "Please find attached offboarding contract.",
        }
        resp = self.client.post("/offboarding/termination/initiate/", data=initiate_data)
        self.assertEqual(resp.status_code, 302)

        termination = TerminationWorkflow.objects.get(employee=self.emp_emp)
        self.assertEqual(termination.status, "initiated")

        # 2. Approve Termination
        resp = self.client.get(f"/offboarding/termination/{termination.id}/approve/")
        self.assertEqual(resp.status_code, 302)
        termination.refresh_from_db()
        self.assertEqual(termination.status, "approved")

        # 3. Update Checklist
        checklist_data = {
            "assets_returned": "on",
            "access_revoked": "on",
        }
        resp = self.client.post(f"/offboarding/termination/{termination.id}/update-checklist/", data=checklist_data)
        self.assertEqual(resp.status_code, 302)
        termination.refresh_from_db()
        self.assertTrue(termination.assets_returned)
        self.assertTrue(termination.access_revoked)

        # 4. Complete / Finalize Offboarding
        resp = self.client.get(f"/offboarding/termination/{termination.id}/complete/")
        self.assertEqual(resp.status_code, 302)
        termination.refresh_from_db()
        self.assertEqual(termination.status, "completed")

        # Employee must be marked as inactive, but data is preserved (not deleted)
        self.emp_emp.refresh_from_db()
        self.assertFalse(self.emp_emp.is_active)

    def test_04_permissions_enforcement(self):
        """Verify that regular employees cannot access templates or other employee's letters/workflows."""
        # Log in as normal employee
        self.client.force_login(self.emp_user)

        # Cannot access templates list
        resp = self.client.get("/employee/joining-letters/templates/")
        self.assertEqual(resp.status_code, 403)

        # Cannot initiate termination
        resp = self.client.get("/offboarding/termination/")
        self.assertEqual(resp.status_code, 403)
