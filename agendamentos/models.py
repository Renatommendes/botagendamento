# agendamentos/models.py

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Agendamento(models.Model):

    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    contato = models.ForeignKey(
        'Contato',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    nome = models.CharField(max_length=100)

    telefone = models.CharField(max_length=15)

    horario = models.DateTimeField()

    confirmado = models.BooleanField(default=False)

    google_event_id = models.CharField(max_length=255,null=True,blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    observacao = models.TextField(blank=True,null=True)

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
    arquivo = models.FileField(upload_to='midias/', null=True, blank=True)
    tipo = models.CharField(max_length=20, null=True, blank=True)
    whatsapp_id = models.CharField(max_length=255, blank=True, null=True)
    empresa = models.ForeignKey(
    'Empresa',
    on_delete=models.CASCADE,
    null=True,
    blank=True
    )

    status = models.CharField(
        max_length=20,
        default="sent"
    )

    def __str__(self):
        direcao = "Recebida" if self.recebida else "Enviada"
        return f"[{direcao}] {self.numero} - {self.texto[:30]}"



class Contato(models.Model):

    empresa = models.ForeignKey(
    'Empresa',
    on_delete=models.CASCADE,
    null=True,
    blank=True
    )

    nome = models.CharField(max_length=100, blank=True, null=True)

    numero = models.CharField(max_length=20)

    criado_em = models.DateTimeField(auto_now_add=True)

    ultima_mensagem_em = models.DateTimeField(default=timezone.now)

    nao_lidas = models.IntegerField(default=0)

    online = models.BooleanField(default=False)

    ultimo_ping = models.DateTimeField(null=True, blank=True)

    digitando = models.BooleanField(default=False)

    etapa_atual = models.ForeignKey("EtapaBot",null=True,blank=True,on_delete=models.SET_NULL)

    em_atendimento_humano = models.BooleanField(
    default=False
    )

    ultimo_atendimento = models.DateTimeField(
        null=True,
        blank=True
    )

    data_temp = models.CharField(
    max_length=30,
    blank=True,
    null=True
    )

    aguardando_data = models.BooleanField(default=False)

    aguardando_horario = models.BooleanField(default=False)

    data_agendamento_temp = models.CharField(
    max_length=20,
    null=True,
    blank=True
    )

    horario_temp = models.CharField(
    max_length=10,
    blank=True,
    null=True
    )



class Empresa(models.Model):

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    nome = models.CharField(max_length=100)

    verify_token = models.CharField(max_length=255)

    whatsapp_access_token = models.TextField()

    whatsapp_phone_number_id = models.CharField(max_length=255)

    google_calendar_id = models.CharField(max_length=255)

    horario_inicio = models.TimeField()

    horario_fim = models.TimeField()

    google_access_token = models.TextField(
    null=True,
    blank=True
    )

    google_refresh_token = models.TextField(
        null=True,
        blank=True
    )

    google_calendar_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.nome


class MensagemBot(models.Model):
    empresa = models.ForeignKey(
    'Empresa',
    on_delete=models.CASCADE,
    null=True,
    blank=True
    )

    chave = models.CharField(max_length=50)

    mensagem = models.TextField()



class UsuarioEmpresa(models.Model):
    FUNCOES = (
        ("admin", "Admin"),
        ("atendente", "Atendente"),
        ("suporte", "Suporte"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    empresa = models.ForeignKey("Empresa", on_delete=models.CASCADE)
    funcao = models.CharField(max_length=20, choices=FUNCOES, default="atendente")

    def __str__(self):
        return f"{self.user.username} - {self.empresa.nome}"



class RegraBot(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    palavra_chave = models.CharField(max_length=100)
    resposta = models.TextField()

    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.palavra_chave


class FluxoBot(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)  # ex: "Fluxo principal"
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


class EtapaBot(models.Model):

    fluxo = models.ForeignKey(
        FluxoBot,
        on_delete=models.CASCADE
    )

    nome = models.CharField(max_length=100)

    mensagem = models.TextField()

    eh_inicial = models.BooleanField(default=False)
    ordem = models.IntegerField(default=0)

    pos_x = models.IntegerField(default=250)
    pos_y = models.IntegerField(default=250)

    def __str__(self):
        return self.nome


class OpcaoBot(models.Model):
    etapa = models.ForeignKey(EtapaBot, on_delete=models.CASCADE)

    texto_opcao = models.CharField(max_length=100)
    # ex: "1 - Agendamento"

    proxima_etapa = models.ForeignKey(
        EtapaBot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proximas_opcoes"
    )

    valor_esperado = models.CharField(max_length=50, blank=True, null=True)
    # ex: "1", "2", "sim", "nao"

    def __str__(self):
        return self.texto_opcao

class ConexaoEtapa(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    de_etapa = models.ForeignKey("EtapaBot", on_delete=models.CASCADE, related_name="saida")
    para_etapa = models.ForeignKey("EtapaBot", on_delete=models.CASCADE, related_name="entrada")
    gatilho = models.CharField(max_length=100, null=True, blank=True)
    opcao = models.ForeignKey("OpcaoBot",null=True,blank=True,on_delete=models.CASCADE)



class UsuarioEstado(models.Model):
    telefone = models.CharField(max_length=20)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    etapa_atual = models.ForeignKey(
        EtapaBot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    atualizado_em = models.DateTimeField(auto_now=True)
