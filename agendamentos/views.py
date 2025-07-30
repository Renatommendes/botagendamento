# agendamentos/views.py
from google_calendar.calendar_utils import buscar_horarios_disponiveis
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
import pytz

# Armazena o estado da conversa: {numero: {"fase": ..., "data": ...}}
conversas_usuarios = {}

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

        estado = conversas_usuarios.get(numero, {})

        if mensagem.lower() == "consulta":
            conversas_usuarios[numero] = {"fase": "aguardando_data"}
            enviar_mensagem(numero, "Qual dia você deseja agendar? Envie no formato AAAA-MM-DD (ex: 2025-08-01)")
        
        elif estado.get("fase") == "aguardando_data":
            try:
                data = datetime.strptime(mensagem.strip(), "%Y-%m-%d").date()
                creds = Credentials.from_authorized_user_file("token.json")
                horarios = buscar_horarios_disponiveis(str(data), creds)
                if horarios:
                    conversas_usuarios[numero] = {"fase": "aguardando_horario", "data": str(data)}
                    resposta = "Horários disponíveis para {}:\n".format(data.strftime("%d/%m/%Y"))
                    resposta += "\n".join(horarios)
                    resposta += "\n\nResponda com o horário desejado (ex: 14:00)."
                else:
                    resposta = "Não há horários disponíveis nesse dia. Tente outra data."
                enviar_mensagem(numero, resposta)
            except ValueError:
                enviar_mensagem(numero, "Formato de data inválido. Use o formato AAAA-MM-DD.")

        elif estado.get("fase") == "aguardando_horario":
            data = estado.get("data")
            horario = mensagem.strip()
            try:
                horario_obj = datetime.strptime(horario, "%H:%M").time()
                inicio = datetime.strptime(f"{data} {horario}", "%Y-%m-%d %H:%M")
                fim = inicio + timedelta(minutes=30)
                tz = pytz.timezone("America/Sao_Paulo")
                inicio = tz.localize(inicio)
                fim = tz.localize(fim)

                creds = Credentials.from_authorized_user_file("token.json")
                service = build("calendar", "v3", credentials=creds)

                evento = {
                    'summary': 'Consulta agendada via WhatsApp',
                    'start': {'dateTime': inicio.isoformat(), 'timeZone': 'America/Sao_Paulo'},
                    'end': {'dateTime': fim.isoformat(), 'timeZone': 'America/Sao_Paulo'},
                }

                service.events().insert(calendarId='primary', body=evento).execute()

                enviar_mensagem(numero, f"✅ Sua consulta foi agendada para {data} às {horario}.")

                conversas_usuarios.pop(numero, None)  # Limpa estado

            except ValueError:
                enviar_mensagem(numero, "Formato de horário inválido. Use HH:MM (ex: 14:00).")
        else:
            enviar_mensagem(numero, "Desculpe, não entendi. Envie 'consulta' para agendar.")
    except KeyError:
        print("Nenhuma mensagem processável recebida.")

    return HttpResponse(status=200)




WHATSAPP_TOKEN = "EAAOZBvOh2pfoBPBwyWZBXNLQ6iNdjMI1SpSkQLhuAlZAPs2FoEOWjMcwvU810Aq5TtKN39WpKGvAwlOxPZAUzZCX0RYdjAZCCq1ZBP4lvbgZAbg3X23m5zB9grKAFAuas3Cp1DXIbwHTmQ9Mu1ZBA0JZBpyuzvvRGN5WdAvb36vbJ0WoJ6HM1cZCSBFDpDgn95FfByg6pkCKyjzldbD7o2jGVAZBRS9PZAQ8H1YiCR1u8tbGpEhrELzkqGacWtHZB5A9u7GwZDZD"
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


    