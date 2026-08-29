from django.db import models


class MobileAttendanceEvidence(models.Model):
    employee = models.ForeignKey("employee.Employee", on_delete=models.CASCADE)
    action = models.CharField(max_length=16, choices=(("clock-in", "Clock in"), ("clock-out", "Clock out")))
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    accuracy = models.FloatField(null=True, blank=True)
    biometric_verified = models.BooleanField(default=False)
    selfie = models.ImageField(upload_to="mobile_attendance/%Y/%m/%d")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
