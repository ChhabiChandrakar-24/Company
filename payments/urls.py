from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("pay/", views.CreatePaymentView.as_view(), name="create_payment"),
    path("verify/", views.VerifyPaymentView.as_view(), name="verify_payment"),
    path("webhook/razorpay/", views.RazorpayWebhookView.as_view(), name="razorpay_webhook"),
    path("webhook/phonepe/", views.PhonePeWebhookView.as_view(), name="phonepe_webhook"),
]
