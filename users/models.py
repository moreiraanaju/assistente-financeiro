import uuid
from django.conf import settings
from django.db import models


class User(models.Model):
    """Perfil de usuário vinculado ao auth.User do Django.

    Armazena o número de WhatsApp e preferências regionais.
    A ligação com auth.User é feita via auth_user (OneToOneField).
    """
    auth_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        null=True,
        blank=True,
    )
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(max_length=100, null=False, blank=False)
    phone_number = models.CharField(max_length=16, unique=True, blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    updated_at = models.DateTimeField(auto_now=True, null=False, blank=False)
    time_zone = models.CharField(max_length=50, default='America/Sao_Paulo')
    locale = models.CharField(max_length=10, default='pt_BR')

    def __str__(self):
        return f"{self.name} ({self.phone_number})"