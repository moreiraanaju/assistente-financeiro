from django.db import models

class Transacao(models.Model):
    tipo = models.CharField(max_length=20)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.TextField(blank=True)
    data = models.DateTimeField(auto_now_add=True)
    categoria = models.CharField(max_length=100)  #sprint 2 da categoria

    def __str__(self):
        return f"{self.tipo} - {self.valor} - {self.categoria}"


        #teste de commit
