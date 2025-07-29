# agendamentos/views.py

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests

# View para testar se app está rodando
def home(request):
    return HttpResponse("✅ Bot do WhatsApp está rodando!")

# Token de verificação usado no Meta Developers
VERIFY_TOKEN = "meu_token_secreto"  # Certifique-se de usar esse mesmo valor no painel da Meta

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == "GET":
        # Usado pelo Meta para verificar o webhook
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return HttpResponse(challenge, status=200)
        else:
            return HttpResponse("Token inválido", status=403)

    elif request.method == "POST":
        body = json.loads(request.body)
    print("Mensagem recebida:", json.dumps(body, indent=2))

    try:
        mensagem = body["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
        numero = body["entry"][0]["changes"][0]["value"]["messages"][0]["from"]

        if mensagem.lower() == "consulta":
            enviar_mensagem(numero, "Olá! Deseja agendar para:\n1. Hoje às 14h\n2. Hoje às 15h")
        else:
            enviar_mensagem(numero, "Desculpe, não entendi. Envie 'consulta' para agendar.")
    except KeyError:
        print("Nenhuma mensagem processável recebida.")
    
    return HttpResponse(status=200)


WHATSAPP_TOKEN = "EAAOZBvOh2pfoBPOYZAyltpkc6BfJflZB4PlKEaqSD2IrKRJAhS3WIeTeploskPm8g7KgLT2ynN34KZCDUFdF9BQjx2ZCOPZBwhPbF6LO3aJ6fZAlM4y3bWmAgDVJa5PI2Uy7nC9jV9H0oX79uq9oMmChlvYRZCKblvU7t8EOyqwM2ZBYt7binkEDqEsS0ntckqJ4jXL4FfDtrdeFIL3us8BPBZAR18ZCbwW58XmfEp77ZBATtToE4HidEipyDonMYjOGYAZDZD"
PHONE_NUMBER_ID = "721759997679627"

def enviar_mensagem(numero_destino, mensagem):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {
            "body": mensagem
        }
    }
    response = requests.post(url, headers=headers, json=data)
    print("Resposta do envio:", response.status_code, response.text)