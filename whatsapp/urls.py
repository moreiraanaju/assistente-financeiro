# whatsapp/urls.py
from django.urls import path
from .views import evolution_webhook

urlpatterns = [
    path("evolution/webhook/", evolution_webhook, name="evolution_webhook"),
]
