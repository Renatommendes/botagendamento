import os
import json
import pytz
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_calendar.calendar_utils import buscar_horarios_disponiveis
from .models import Cliente, Mensagem
from django.shortcuts import render, redirect
from .forms import ClienteForm
from django.views.decorators.http import require_POST

# Armazena o estado da conversa por número
conversas_usuarios = {}

# Token para verificação do webhook Meta
VERIFY_TOKEN = "meu_token_secreto"

WHATSAPP_PHONE_NUMBER_ID = "808249715700922"
WHATSAPP_ACCESS_TOKEN = "EAAOBZCDzkrjcBPRdJ3VwffHDcosZBI5Mkj3Xq6iDkCSZA56ZCCEV9Sqqt0HZBKxVfEd2jZCqJXIrGgqycOJ4vggflAOf2ypcS5LphaV5g160a7LQUoiVtyUaZBXfYXlhaNsOzGuukQU8zo0a0ti29ztNTzUAsZAHI1ecsm6ury3bXibXdEj7py51QGVIZA72XzZAyU37KK6rBVdbJxR3SgetsMez4onMBq8LQLiZBkUuQ0K"


def home(request):
    return HttpResponse("✅ Bot do WhatsApp está rodando!")

def tela_inicial(request):
    return render(request, 'tela_inicial.html')


def painel(request):
    return render(request, 'chat/painel.html')


@csrf_exempt
def webhook(request):
    if request.method == "GET":
        verify_token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if verify_token == VERIFY_TOKEN:
            return HttpResponse(challenge)
        else:
            return HttpResponse("Token inválido", status=403)

    elif request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        print("Mensagem recebida:", json.dumps(data, indent=2, ensure_ascii=False))

        try:
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    messages = value.get('messages', [])
                    for message in messages:
                        numero = message.get('from')
                        texto = message.get('text', {}).get('body', '')
                        # Salvar no banco
                        Mensagem.objects.create(
                            numero=numero,
                            texto=texto,
                            recebida=True
                        )
                        print(f"Mensagem salva de {numero}: {texto}")
        except Exception as e:
            print(f"Erro ao salvar mensagem: {e}")

        return HttpResponse("EVENT_RECEIVED")

    return HttpResponse("Método não suportado", status=405)


def enviar_mensagem(cliente, numero_destino, mensagem):
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": mensagem}
    }
    response = requests.post(url, headers=headers, json=data)

    # Salvar mensagem enviada
    Mensagem.objects.create(
        cliente=cliente,
        numero=numero_destino,
        texto=mensagem,
        recebida=False
    )

    print("Resposta do envio:", response.status_code, response.text)


def listar_clientes(request):
    clientes = Cliente.objects.all()
    return render(request, 'clientes/listar.html', {'clientes': clientes})


def novo_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('listar')
    else:
        form = ClienteForm()
    return render(request, 'clientes/novo.html', {'form': form})


def painel_chat(request, numero=None):
    # Junta os contatos vindos das mensagens + os telefones de clientes
    numeros_msg = set(Mensagem.objects.values_list("numero", flat=True))
    numeros_cli = set(Cliente.objects.values_list("telefone", flat=True))
    contatos = sorted(numeros_msg.union(numeros_cli))

    if not numero and contatos:
        numero = contatos[0]  # pega o primeiro da lista

    mensagens = []
    if numero:
        mensagens = Mensagem.objects.filter(numero=numero).order_by("data_hora")

    return render(request, "chat/painel.html", {
        "numeros": contatos,
        "mensagens": mensagens,
        "numero_atual": numero,
    })


def conversa(request, numero):
    mensagens = Mensagem.objects.filter(numero=numero).order_by("data_hora")
    cliente = Cliente.objects.filter(telefone=numero).first()

    return render(request, "chat/painel.html", {
        "mensagens": mensagens,
        "numero_atual": numero,
        "cliente": cliente
    })


@require_POST
def responder_mensagem(request, numero):
    texto = request.POST.get("mensagem")
    cliente = Cliente.objects.filter(telefone=numero).first()
    enviar_mensagem(cliente, numero, texto)

    # Redireciona para o chat do número após enviar
    return redirect("painel_chat_numero", numero=numero)


def enviar_template(numero, nome="Cliente"):
    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "template",
        "template": {
            "name": "boas_vindas",  # nome do template aprovado
            "language": {"code": "pt_BR"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": nome},
                    ]
                }
            ]
        }
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()


@require_POST
def adicionar_contato(request):
    numero = (request.POST.get("numero") or "").strip()
    if not numero:
        return redirect("painel_chat")

    # Normaliza: mantém só dígitos
    numero = "".join(ch for ch in numero if ch.isdigit())

    # Cria um cliente se ainda não existir
    cliente, created = Cliente.objects.get_or_create(telefone=numero)

    # Opcional: dispara mensagem inicial (template)
    enviar_template(numero, cliente.nome or "Cliente")

    return redirect("painel_chat_numero", numero=numero)
