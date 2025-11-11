from django.db import models

class Message(models.Model):
    external_id = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.external_id