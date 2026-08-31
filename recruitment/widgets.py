"""
widgets.py

This page is used to write custom form widget or override some functionalities.

"""

from django import forms
from django.templatetags.static import static
from django.utils.safestring import mark_safe

# your your widgets


class RecruitmentAjaxWidget(forms.Widget):
    """
    This widget class is used to load the ajax script for the recruitment,
    the job position and to the stage.
    """

    def render(self, name, value, attrs=None, renderer=None):
        # Exclude the label from the rendered HTML
        stylesheet_url = static("recruitment/widget/recruitment_widget_style.css")
        script_url = static("recruitment/widget/recruitmentAjax.js")
        rendered_script = (
            f'<link rel="stylesheet" href="{stylesheet_url}">'
            f'<script src="{script_url}"></script>'
        )

        additional_script = f"""
        <script id="{name}Script">
            $(document).ready(function () {{
                $("[for='id_{name}']").remove()
                $("#{name}Script").remove()
            }});
        </script>
        """
        attrs = attrs or {}
        attrs["required"] = False
        return mark_safe(rendered_script + additional_script)
