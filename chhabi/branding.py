"""UI branding helpers for the local Geeta Forgetech deployment."""

import re


class GeetaForgetechBrandingMiddleware:
    """Replace the upstream product name in user-facing text responses."""

    replacements = (
        (b"CHHABI", b"GEETA FORGETECH"),
        (b"Chhabi", b"Geeta Forgetech"),
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get("Content-Type", "")
        if not getattr(response, "streaming", False) and (
            content_type.startswith("text/")
            or "javascript" in content_type
            or "json" in content_type
        ):
            content = response.content
            for old, new in self.replacements:
                content = content.replace(old, new)
            # Remove upstream promotional/back links from rendered UI while
            # retaining local routes and third-party library functionality.
            content = re.sub(
                rb"href=([\"'])https?://(?:www\.)?(?:chhabi\.com|github\.com/chhabi-opensource)[^\"']*\1",
                b'href="#"',
                content,
                flags=re.IGNORECASE,
            )
            response.content = content
            response["Content-Length"] = str(len(content))
        return response
