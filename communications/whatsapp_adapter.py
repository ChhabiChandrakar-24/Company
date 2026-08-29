import logging
from django.conf import settings
from django.utils import timezone
from .models import CommunicationLog
from base.models import EmailLog

logger = logging.getLogger(__name__)

class WhatsAppAdapterBase:
    """Base class for WhatsApp adapters.

    Subclasses must implement :meth:`send_message`.
    """
    def send_message(self, template_name: str, recipient: str, context: dict) -> str:
        raise NotImplementedError("WhatsAppAdapterBase.send_message must be overridden")

class MockWhatsAppAdapter(WhatsAppAdapterBase):
    """A mock adapter that logs the message and pretends it was sent.

    This is useful for development and testing before a real provider is
    integrated.
    """
    def send_message(self, template_name: str, recipient: str, context: dict) -> str:
        # Render a simple message using the template name and context.
        # In a real implementation you would load a template file and render it.
        message = f"[Mock WhatsApp] Template: {template_name}, To: {recipient}, Context: {context}"
        logger.info(message)
        # Record in CommunicationLog
        CommunicationLog.objects.create(
            channel='whatsapp',
            subject=template_name,
            body=message,
            status="sent",
            client=None,  # filled by view later
            response_data={"mock": True, "message": message},
        )
        return "sent"

def get_adapter():
    """Instantiate the adapter class defined in ``settings.WHATSAPP_ADAPTER``.

    The setting should be a dotted path to a subclass of ``WhatsAppAdapterBase``.
    If the setting is missing or import fails, we fall back to ``MockWhatsAppAdapter``.
    """
    adapter_path = getattr(settings, "WHATSAPP_ADAPTER", "communications.whatsapp_adapter.MockWhatsAppAdapter")
    try:
        module_path, class_name = adapter_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        klass = getattr(module, class_name)
        if not issubclass(klass, WhatsAppAdapterBase):
            raise TypeError(f"{adapter_path} is not a subclass of WhatsAppAdapterBase")
        return klass()
    except Exception as exc:  # pragma: no cover – defensive fallback
        logger.exception("Failed to load WhatsApp adapter %s, using mock", adapter_path)
        return MockWhatsAppAdapter()
