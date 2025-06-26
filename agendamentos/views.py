# agendamentos/views.py

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json

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
        try:
            body = json.loads(request.body)
            print("📩 Mensagem recebida do WhatsApp:")
            print(json.dumps(body, indent=2))  # log com indentação para facilitar leitura

            # Aqui você pode extrair os dados e tratar a mensagem recebida
            # Exemplo básico:
            entry = body.get("entry", [])[0]
            changes = entry.get("changes", [])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            if messages:
                message = messages[0]
                texto = message["text"]["body"]
                telefone = message["from"]
                print(f"Mensagem: '{texto}' de {telefone}")

                # Aqui você pode chamar uma função para responder, ex:
                # enviar_mensagem(telefone, "Mensagem recebida com sucesso!")

        except Exception as e:
            print("❌ Erro ao processar mensagem:", e)

        return HttpResponse(status=200)

    else:
        return HttpResponse("Método não suportado", status=405)
