# agendamentos/views.py

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json

VERIFY_TOKEN = "meu_token_secreto"

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return HttpResponse(challenge, status=200)
        else:
            return HttpResponse("Token inválido", status=403)

    elif request.method == "POST":
        body = json.loads(request.body)
        print("Mensagem recebida:", body)
        # Trate a mensagem aqui
        return HttpResponse(status=200)
