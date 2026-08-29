from chhabi.settings import TEMPLATES

TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "chhabi_crumbs.context_processors.breadcrumbs",
)
