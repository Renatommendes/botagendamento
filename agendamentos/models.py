# agendamentos/models.py

from django.db import models
from django.utils import timezone

class Agendamento(models.Model):
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=15)
    horario = models.DateTimeField()
    confirmado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nome} - {self.horario.strftime('%d/%m %H:%M')}"


class Cliente(models.Model):
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20, unique=True)
    whatsapp_token = models.TextField()
    phone_number_id = models.CharField(max_length=100)
    google_credentials = models.FileField(upload_to="credenciais/", null=True, blank=True)

    def __str__(self):
        return self.nome


class Mensagem(models.Model):
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE, null=True, blank=True)
    numero = models.CharField(max_length=20)
    texto = models.TextField()
    recebida = models.BooleanField(default=True)  # True = do cliente para nós
    data_hora = models.DateTimeField(default=timezone.now)

    def __str__(self):
        direcao = "Recebida" if self.recebida else "Enviada"
        return f"[{direcao}] {self.numero} - {self.texto[:30]}"


class Contato(models.Model):
    nome = models.CharField(max_length=100, blank=True, null=True)
    numero = models.CharField(max_length=20, unique=True)  # Ex: 5599999999999
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome or self.numero}"
