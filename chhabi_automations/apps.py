"""
App configuration for the Chhabi Automations app.
Initializes model choices and starts automation when the server runs.
"""

import os
import sys

from django.apps import AppConfig


class ChhabiAutomationConfig(AppConfig):
    """Configuration class for the Chhabi Automations Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "chhabi_automations"

    def ready(self):
        """Run initialization tasks when the app is ready."""
        from base.templatetags.chhabifilters import app_installed
        from employee.models import Employee
        from chhabi_automations.methods.methods import get_related_models
        from chhabi_automations.models import MODEL_CHOICES as model_choices

        # Build MODEL_CHOICES
        models = [Employee]
        if app_installed("recruitment"):
            from recruitment.models import Candidate

            models.append(Candidate)

        for main_model in models:
            for model in get_related_models(main_model):
                model_choices.append(
                    (f"{model.__module__}.{model.__name__}", model.__name__)
                )

        model_choices.append(("employee.models.Employee", "Employee"))
        model_choices.append(("pms.models.EmployeeKeyResult", "Employee Key Results"))
        # Keep the dynamic choices deterministic so migration state does not
        # change merely because Python set ordering changed between processes.
        model_choices[:] = sorted(set(model_choices))

        # Only start automation when running the server
        if (
            len(sys.argv) >= 2
            and sys.argv[1] == "runserver"
            and os.environ.get("RUN_MAIN") == "true"
        ):
            from chhabi_automations.signals import start_automation

            start_automation()
