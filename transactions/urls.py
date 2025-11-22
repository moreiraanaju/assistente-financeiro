from django.urls import path
from . import views
from .views import WebhookTransactionView

urlpatterns = [    
  # roda da feature gustavo (webhook)
  path("webhook/", WebhookTransactionView.as_view(), name="webhook"),
]

