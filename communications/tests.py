from django.test import TestCase
from communications.models import CommunicationLog
from communications.email_adapter import EmailAdapter
from communications.whatsapp_adapter import MockWhatsAppAdapter
from crm.models import CRMClient

class CommunicationAdapterTests(TestCase):
    def setUp(self):
        self.client = CRMClient.objects.create(
            email='test@example.com',
            name='Test Client',
            company_name='TestCo',
            phone='1234567890',
            status='lead',
        )

    def test_email_adapter_creates_log(self):
        subject = 'Test Subject'
        body = 'Test Body'
        EmailAdapter.send_email(subject, body, [self.client.email])
        log = CommunicationLog.objects.get(subject=subject)
        self.assertEqual(log.channel, 'email')
        self.assertEqual(log.body, body)
        self.assertIsNone(log.client)

    def test_whatsapp_adapter_creates_log(self):
        adapter = MockWhatsAppAdapter()
        template_name = 'welcome_template'
        context = {'message': 'Hello'}
        adapter.send_message(template_name, self.client.phone, context)
        log = CommunicationLog.objects.get(subject=template_name)
        self.assertEqual(log.channel, 'whatsapp')
        self.assertIn('Mock WhatsApp', log.body)
        self.assertIsNone(log.client)
