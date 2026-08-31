import calendar
import datetime as dt
import os
import sys
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from dateutil.relativedelta import relativedelta


def leave_reset():
    from leave.models import LeaveType

    today = datetime.now()
    today_date = today.date()
    leave_types = LeaveType.objects.filter(reset=True)
    # Looping through filtered leave types with reset is true
    for leave_type in leave_types:
        # Looping through all available leaves
        available_leaves = leave_type.employee_available_leave.all()

        for available_leave in available_leaves:
            reset_date = available_leave.reset_date
            expired_date = available_leave.expired_date
            if reset_date == today_date:
                available_leave.update_carryforward()
                # new_reset_date = available_leave.set_reset_date(assigned_date=today_date,available_leave = available_leave)
                new_reset_date = available_leave.set_reset_date(
                    assigned_date=today_date, available_leave=available_leave
                )
                available_leave.reset_date = new_reset_date
                available_leave.save()
            if expired_date and expired_date <= today_date:
                new_expired_date = available_leave.set_expired_date(
                    available_leave=available_leave, assigned_date=today_date
                )
                available_leave.expired_date = new_expired_date
                available_leave.save()

        if (
            leave_type.carryforward_expire_date
            and leave_type.carryforward_expire_date <= today_date
        ):
            leave_type.carryforward_expire_date = leave_type.set_expired_date(
                today_date
            )
            leave_type.save()


_scheduler = None


def start_scheduler():
    """
    Start background leave tasks after Django's app registry is ready.

    Django's development server imports applications once in the autoreloader
    parent and again in the serving child, so only start in the child process.
    """
    global _scheduler

    skipped_commands = {
        "makemigrations",
        "migrate",
        "collectstatic",
        "compilemessages",
        "flush",
        "shell",
        "check",
        "test",
    }
    if any(command in sys.argv for command in skipped_commands):
        return
    if (
        "runserver" in sys.argv
        and "--noreload" not in sys.argv
        and os.environ.get("RUN_MAIN") != "true"
    ):
        return
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        leave_reset,
        "interval",
        seconds=20,
        id="leave_reset",
        replace_existing=True,
    )
    _scheduler.start()
