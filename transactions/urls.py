from django.urls import path
from . import views
from .views import TransacaoCreateView

urlpatterns = [    
  # roda da feature gustavo (webhook)
    path("webhook/", views.webhook, name="webhook"),
]

urlpatterns = [
  # rota da Main (api direta ana ju)
    path('transacao/', TransacaoCreateView.as_view(), name='criar_transacao'),
]

