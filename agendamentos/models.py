# agendamentos/models.py

from django.db import models

class Agendamento(models.Model):
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=15)
    horario = models.DateTimeField()
    confirmado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nome} - {self.horario.strftime('%d/%m %H:%M')}"
