"""Template helpers for the GFT public website."""
import re

from django import template

register = template.Library()

_ICON_MAP = {
    "home": "fa-house",
    "services": "fa-layer-group",
    "solutions": "fa-cubes",
    "products": "fa-box-open",
    "industries": "fa-building-columns",
    "resources": "fa-book-open",
    "company": "fa-flag",
    "about": "fa-circle-info",
    "contact": "fa-envelope",
    "contact us": "fa-envelope",
    "team": "fa-users",
    "careers": "fa-briefcase",
    "career": "fa-briefcase",
    "pricing": "fa-tags",
    "faq": "fa-circle-question",
    "faqs": "fa-circle-question",
    "projects": "fa-diagram-project",
    "portfolio": "fa-images",
    "blog": "fa-newspaper",
    "insights": "fa-lightbulb",
    "terms": "fa-file-contract",
    "terms & conditions": "fa-file-contract",
    "web development": "fa-code",
    "mobile": "fa-mobile-screen",
    "mobile applications": "fa-mobile-screen",
    "cloud": "fa-cloud",
    "cloud & devops": "fa-cloud",
    "cyber": "fa-shield-halved",
    "cyber security": "fa-shield-halved",
    "security": "fa-shield-halved",
    "erp": "fa-cubes-stacked",
    "ai": "fa-robot",
    "data": "fa-chart-line",
    "ui": "fa-pen-ruler",
    "ux": "fa-pen-ruler",
    "design": "fa-pen-ruler",
    "automation": "fa-gears",
    "testing": "fa-vial-circle-check",
    "devops": "fa-cloud-arrow-up",
    "education": "fa-graduation-cap",
    "healthcare": "fa-heart-pulse",
    "fintech": "fa-money-bill-trend-up",
    "finance": "fa-building-columns",
    "manufacturing": "fa-industry",
    "retail": "fa-cart-shopping",
    "logistics": "fa-truck-fast",
    "government": "fa-landmark",
}


def _fallback_icon(label):
    """Pick a sensible icon from the first keyword that matches the label."""
    lowered = (label or "").lower()
    for key, icon in _ICON_MAP.items():
        if key in lowered:
            return icon
    return "fa-angles-right"


@register.filter
def menu_icon(item):
    """Return a Font Awesome class for a NavigationItem/HeaderMenuItem label."""
    label = (getattr(item, "label", "") or "").strip().lower()
    if label in _ICON_MAP:
        return _ICON_MAP[label]
    return _fallback_icon(label)


@register.filter
def initials(name):
    """Two-letter initials from a person's name, e.g. 'Rahul Mehta' -> 'RM'."""
    parts = re.split(r"\s+", (name or "").strip())
    letters = [p[0].upper() for p in parts if p][:2]
    return "".join(letters) or "?"


@register.filter
def startswith(value, arg):
    """True if the string starts with the given prefix."""
    return str(value or "").startswith(str(arg or ""))


@register.filter
def first_word(value):
    """First word of a string, used for brand-mark fallbacks."""
    value = (value or "").strip()
    return value[0].upper() if value else "G"
