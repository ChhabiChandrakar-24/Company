import logging
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.db import transaction

from .models import CommunicationLog
from base.models import EmailLog

logger = logging.getLogger(__name__)

class EmailAdapter:
    """Simple wrapper around Django's email backend.

    It creates a :class:`CommunicationLog` entry with ``channel='email'`` and
    optionally links to the historic :class:`base.models.EmailLog` for backward
    compatibility.
    """

    @staticmethod
    def send_email(subject: str, body: str, recipient_list, from_email=None, attachments=None, **extra):
        """Send an email and record a communication log.

        Args:
            subject: Email subject line.
            body: Rendered HTML/plain‑text body.
            recipient_list: List of email addresses.
            from_email: Sender address; defaults to ``settings.DEFAULT_FROM_EMAIL``.
            attachments: Iterable of (filename, content, mime) tuples.
            **extra: Additional kwargs passed to ``EmailMessage``.
        """
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        email = EmailMessage(subject, body, from_email, recipient_list, **extra)
        if attachments:
            for attachment in attachments:
                email.attach(*attachment)
        try:
            email.send()
            status = "sent"
        except Exception as exc:  # pragma: no cover – handled in tests via mock
            logger.exception("Failed to send email: %s", exc)
            status = "failed"

        # Record in CommunicationLog inside a transaction so the FK to EmailLog
        # (if created) is consistent.
        with transaction.atomic():
            # Create a legacy EmailLog entry for compatibility.
            email_log = EmailLog.objects.create(
                subject=subject,
                body=body,
                from_email=from_email,
                to=",".join(recipient_list),
                status=status,
                created_at=timezone.now(),
                company_id=getattr(settings, "COMPANY_ID", None),
            )
            CommunicationLog.objects.create(
                channel='email',
                subject=subject,
                body=body,
                status=status,
                client=None,  # Filled later by view when client context is known
                email_log=email_log,
                response_data={},
            )
        return status
