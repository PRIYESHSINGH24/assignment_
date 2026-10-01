from django.urls import path
from payments.views import PaymentCreateView, PaymentProcessView, PaymentWebhookView

app_name = 'payments'

urlpatterns = [
    path('', PaymentCreateView.as_view(), name='create'),
    path('process/', PaymentProcessView.as_view(), name='process'),
    path('webhook/', PaymentWebhookView.as_view(), name='webhook'),
]