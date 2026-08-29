from django.test import Client
import django.conf
django.conf.settings.ALLOWED_HOSTS.append('testserver')
c=Client()
c.force_login(User.objects.filter(is_superuser=True).first())
print('Status:', c.get('/crm/deals/').status_code)
