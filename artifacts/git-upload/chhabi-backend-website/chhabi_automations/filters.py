"""
chhabi_automations/filters.py
"""

from chhabi.filters import ChhabiFilterSet, django_filters
from chhabi_automations.models import MailAutomation


class AutomationFilter(ChhabiFilterSet):
    """
    AutomationFilter
    """

    search = django_filters.CharFilter(field_name="title", lookup_expr="icontains")

    class Meta:
        model = MailAutomation
        fields = "__all__"
