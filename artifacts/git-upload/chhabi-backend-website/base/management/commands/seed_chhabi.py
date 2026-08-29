from django.contrib.auth.models import Permission, User
from django.core.management.base import BaseCommand
from django.db import transaction

from base.models import Company, Department, JobPosition, JobRole
from employee.models import Employee, EmployeeWorkInformation


class Command(BaseCommand):
    help = "Create the Geeta Forgetech company and standard local accounts."

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
                "icon": "company_logo/geeta-forgetech-logo.jpeg",
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

        accounts = [
            ("admin", "Admin@123", "Admin", True, True),
            ("hr", "HR@12345", "HR", True, False),
            ("manager", "Manager@123", "Manager", True, False),
            ("employee", "Employee@123", "Employee", False, False),
        ]
        users = {}
        for index, (username, password, first_name, is_staff, is_superuser) in enumerate(
            accounts, start=1
        ):
            email = f"{username}@geetaforgetech.local"
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": "User",
                    "email": email,
                    "is_staff": is_staff,
                    "is_superuser": is_superuser,
                },
            )
            user.set_password(password)
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.save()
            employee, _ = Employee.objects.get_or_create(
                employee_user_id=user,
                defaults={
                    "employee_first_name": first_name,
                    "employee_last_name": "User",
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

        users["hr"].user_permissions.set(Permission.objects.all())
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
        self.stdout.write(self.style.SUCCESS("Geeta Forgetech accounts seeded."))
