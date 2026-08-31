"""Safe accessors for company logo files."""

from django.contrib.staticfiles import finders
from django.templatetags.static import static


DEFAULT_COMPANY_LOGO = "chhabi/geeta-forgetech-logo.jpeg"


def company_logo_url(company):
    """Return a usable company logo URL, falling back for stale file records."""
    icon = getattr(company, "icon", None)
    name = getattr(icon, "name", None)
    if name:
        try:
            if icon.storage.exists(name):
                return icon.url
        except Exception:  # Storage backends raise backend-specific exceptions.
            pass
    return static(DEFAULT_COMPANY_LOGO)


def open_company_logo(company):
    """Open a stored company logo, or return ``None`` when it is unavailable."""
    icon = getattr(company, "icon", None)
    name = getattr(icon, "name", None)
    if not name:
        return None
    try:
        if icon.storage.exists(name):
            return icon.storage.open(name, "rb")
    except Exception:  # Storage backends raise backend-specific exceptions.
        pass
    return None


def open_default_company_logo():
    """Open the bundled logo without assuming collectstatic has already run."""
    logo_path = finders.find(DEFAULT_COMPANY_LOGO)
    if not logo_path:
        return None
    try:
        return open(logo_path, "rb")
    except OSError:
        return None
