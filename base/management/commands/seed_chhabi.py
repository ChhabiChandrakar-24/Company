from datetime import timedelta
from django.contrib.auth.models import Permission, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from base.models import Company, Department, JobPosition, JobRole
from employee.models import Employee, EmployeeWorkInformation
from pms.models import MeetingPlan, UserSubscription, DeveloperApiKey
from pms.subscription_views import seed_default_plans_if_empty


class Command(BaseCommand):
    help = "Seed company, user accounts, credentials, subscriptions, and developer API keys."

    @transaction.atomic
    def handle(self, *args, **options):
        company, _ = Company.objects.get_or_create(
            company="Geeta Forgetech",
            address="India",
            defaults={
                "hq": True,
                "country": "India",
                "state": "Delhi",
                "city": "New Delhi",
                "zip": "110001",
            },
        )

        departments = list(Department.objects.filter(department="Administration"))
        department = departments[0] if departments else None
        if department is None:
            Department.objects.bulk_create([Department(department="Administration")])
            department = Department.objects.get(department="Administration")
        for duplicate in departments[1:]:
            duplicate.delete()
        department.company_id.add(company)

        position, _ = JobPosition.objects.get_or_create(
            job_position="Administration", department_id=department
        )
        position.company_id.add(company)
        role, _ = JobRole.objects.get_or_create(
            job_position_id=position, job_role="Administrator"
        )
        role.company_id.add(company)

        # Standard User Accounts & New Passwords
        accounts = [
            ("admin", "Admin@2026!Live", "Super", "Admin", True, True),
            ("hr", "Hr@2026!Live", "HR", "Manager", True, False),
            ("manager", "Manager@2026!Live", "Team", "Manager", True, False),
            ("employee", "Employee@2026!Live", "Standard", "Employee", False, False),
            ("developer", "Dev@2026!Live", "API", "Developer", True, False),
        ]
        users = {}
        for index, (username, password, first_name, last_name, is_staff, is_superuser) in enumerate(
            accounts, start=1
        ):
            email = f"{username}@geetaforgetech.local"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "is_staff": is_staff,
                    "is_superuser": is_superuser,
                },
            )
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.set_password(password)
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.save()

            employee, _ = Employee.objects.get_or_create(
                employee_user_id=user,
                defaults={
                    "employee_first_name": first_name,
                    "employee_last_name": last_name,
                    "email": email,
                    "phone": f"900000000{index}",
                    "badge_id": f"GF-{index:03d}",
                },
            )
            EmployeeWorkInformation.objects.update_or_create(
                employee_id=employee,
                defaults={
                    "department_id": department,
                    "job_position_id": position,
                    "job_role_id": role,
                    "company_id": company,
                    "email": email,
                },
            )
            users[username] = user

        # Set specific permissions
        if "hr" in users:
            users["hr"].user_permissions.set(Permission.objects.all())
        if "manager" in users:
            users["manager"].user_permissions.set(
                Permission.objects.filter(
                    codename__in=[
                        "view_employee",
                        "view_recruitment",
                        "view_attendance",
                        "view_leaverequest",
                        "view_payslip",
                        "view_asset",
                        "view_objective",
                        "view_meetings",
                        "add_meetings",
                        "change_meetings",
                        "start_meeting",
                        "record_meeting",
                        "manage_meeting_integrations",
                        "view_meetingnote",
                        "add_meetingnote",
                        "view_meetingrecording",
                        "delete_meetingrecording",
                    ]
                )
            )

        # Seed Default Meeting Plans
        seed_default_plans_if_empty()
        pro_plan = MeetingPlan.objects.filter(code="pro_monthly").first()

        # Seed Active Pro Subscription & API Key for Admin and Developer
        for target_user in [users.get("admin"), users.get("developer")]:
            if target_user and pro_plan:
                sub, _ = UserSubscription.objects.update_or_create(
                    user=target_user,
                    defaults={
                        "plan": pro_plan,
                        "peer_seats": 5,
                        "start_date": timezone.now(),
                        "end_date": timezone.now() + timedelta(days=365),
                        "status": "active",
                        "payment_gateway": "free",
                    },
                )
                DeveloperApiKey.objects.update_or_create(
                    user=target_user,
                    app_name=f"{target_user.username.title()} Production Video App",
                    defaults={
                        "subscription": sub,
                        "api_key": f"hrz_live_{target_user.username}_key_2026",
                        "api_secret": f"sec_live_{target_user.username}_secret_2026",
                        "is_active": True,
                        "rate_limit_per_minute": 120,
                    },
                )

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS(" SUCCESS: ALL ACCOUNTS & PASSWORDS SEEDED IN DATABASE! "))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        for username, password, first, last, _, _ in accounts:
            self.stdout.write(f"  • Username: {username.ljust(12)} | Password: {password}")
        self.stdout.write(self.style.SUCCESS("=" * 60))
