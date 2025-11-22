# whatsapp/urls.py
from django.urls import path
from .views import evolution_webhook

urlpatterns = [
    path("webhook/", evolution_webhook, name="evolution_webhook"),
]
