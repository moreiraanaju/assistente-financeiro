from django.urls import path
from . import views
from .views import WebhookTransactionView, TransactionCreateView, ConsultaView, InsightsView

urlpatterns = [
  path("webhook/", WebhookTransactionView.as_view(), name="webhook"),
  path("transacao/", TransactionCreateView.as_view(), name="transacao"),
  path("consulta/", ConsultaView.as_view(), name="consulta"),
  path("insights/", InsightsView.as_view(), name="insights"),
]

