"""Safe accessors for company logo files."""

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
