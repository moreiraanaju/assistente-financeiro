from django.conf import settings
from django.db import models
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return self.name


class Transacao(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True,
        blank=True)
    message = models.ForeignKey("whatsapp.Message", on_delete=models.PROTECT, null=True, blank=True)

    description = models.CharField(max_length=255)
    date_transaction = models.DateTimeField(default=timezone.now, db_index=True)

    value = models.DecimalField(max_digits=10, decimal_places=2)

    TRANSACTION_TYPES = [
        ("IN", "Income"),
        ("OUT", "Expense"),
        ("TRANS", "Transference"),
    ]
    type = models.CharField(max_length=5, choices=TRANSACTION_TYPES)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # bloqueia alteração de value após criação
        if self.pk is not None:
            old = type(self).objects.only("value").get(pk=self.pk)
            if old.value != self.value:
                raise ValueError("value não pode ser alterado após criação.")
        return super().save(*args, **kwargs)

    def __str__(self):
        # use o rótulo legível do choices
        return f"{self.get_type_display()} - {self.value} ({self.category})"

    class Meta:
        ordering = ["-date_transaction", "-id"]
        indexes = [
            models.Index(fields=["user", "date_transaction"]),
            models.Index(fields=["type"]),
        ]