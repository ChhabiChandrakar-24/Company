from django.db import models

# Create your models here.


class LDAPSettings(models.Model):
    ldap_server = models.CharField(max_length=255, default="ldap://127.0.0.1:389")
    bind_dn = models.CharField(max_length=255, default="cn=admin,dc=chhabi,dc=com")
    bind_password = models.CharField(max_length=255)
    base_dn = models.CharField(max_length=255, default="ou=users,dc=chhabi,dc=com")

    def __str__(self):
        return f"LDAP Settings ({self.ldap_server})"
