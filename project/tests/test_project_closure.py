import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite

from project.models import Project, Task, ProjectClosure, ProjectCommunicationLog
from project.admin import ProjectAdmin, mark_as_completed

User = get_user_model()

class MockRequest:
    def __init__(self, user):
        self.user = user
        self.session = {}
        self._messages = []

    @property
    def messages(self):
        return self._messages

class ProjectClosureAdminTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username="admin", email="admin@example.com", password="adminpass")
        self.client = Client()
        self.client.login(username="admin", password="adminpass")
        self.project = Project.objects.create(
            title="Test Project",
            start_date="2023-01-01",
            end_date="2023-12-31",
            status="in_progress",
            description="Test description",
            company_id=None,
        )
        self.task = Task.objects.create(
            title="Task 1",
            project=self.project,
            status="completed",
            description="Task description",
        )
        self.admin = ProjectAdmin(Project, AdminSite())

    def test_mark_as_completed_creates_closure_and_logs(self):
        qs = Project.objects.filter(id=self.project.id)
        request = MockRequest(self.admin_user)
        mark_as_completed(self.admin, request, qs)
        closure = ProjectClosure.objects.get(project=self.project)
        self.assertEqual(closure.delivery_status, "verified")
        self.assertEqual(closure.payment_status, "verified")
        self.assertIsNotNone(closure.closed_at)
        log = ProjectCommunicationLog.objects.filter(project=self.project, channel="email").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, "sent")
