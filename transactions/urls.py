from django.urls import path
from .views import TransacaoCreateView

urlpatterns = [
    path('transacao/', TransacaoCreateView.as_view(), name='criar_transacao'),
]
