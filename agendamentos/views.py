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

# Armazena o estado da conversa
conversas_usuarios = {}

# Verificação Meta
VERIFY_TOKEN = "meu_token_secreto"

# Token e ID do número do WhatsApp
WHATSAPP_TOKEN = "meu token"
PHONE_NUMBER_ID = "721759997679627"

def home(request):
    return HttpResponse("✅ Bot do WhatsApp está rodando!")

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
        print("Mensagem recebida:", json.dumps(body, indent=2))

        try:
            mensagem = body["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
            numero = body["entry"][0]["changes"][0]["value"]["messages"][0]["from"]

            estado = conversas_usuarios.get(numero, {})
            token_path = os.path.join(settings.BASE_DIR, 'token.json')

            if mensagem.lower() == "consulta":
                conversas_usuarios[numero] = {"fase": "aguardando_nome"}
                enviar_mensagem(numero, "Qual seu nome completo?")

            elif estado.get("fase") == "aguardando_nome":
                nome = mensagem.strip()
                conversas_usuarios[numero] = {
                    "fase": "aguardando_data",
                    "nome": nome
                }
                enviar_mensagem(numero, f"Olá {nome}! Qual dia você deseja agendar? Envie no formato DD/MM/AAAA (ex: 01/08/2025)")

            elif estado.get("fase") == "aguardando_data":
                try:
                    data = datetime.strptime(mensagem.strip(), "%d/%m/%Y").date()
                    creds = Credentials.from_authorized_user_file(token_path)
                    horarios = buscar_horarios_disponiveis(str(data), creds)

                    if horarios:
                        conversas_usuarios[numero]["fase"] = "aguardando_horario"
                        conversas_usuarios[numero]["data"] = str(data)
                        resposta = f"Horários disponíveis para {data.strftime('%d/%m/%Y')}:\n"
                        resposta += "\n".join(horarios)
                        resposta += "\n\nResponda com o horário desejado (ex: 14:00)."
                    else:
                        resposta = "❌ Não há horários disponíveis nesse dia. Tente outra data."

                    enviar_mensagem(numero, resposta)
                except ValueError:
                    enviar_mensagem(numero, "⚠️ Formato de data inválido. Use DD/MM/AAAA (ex: 01/08/2025).")

            elif estado.get("fase") == "aguardando_horario":
                data = estado.get("data")
                nome = estado.get("nome")
                horario = mensagem.strip()

                try:
                    horario_obj = datetime.strptime(horario, "%H:%M").time()
                    inicio = datetime.strptime(f"{data} {horario}", "%Y-%m-%d %H:%M")
                    fim = inicio + timedelta(minutes=30)
                    tz = pytz.timezone("America/Sao_Paulo")
                    inicio = tz.localize(inicio)
                    fim = tz.localize(fim)

                    creds = Credentials.from_authorized_user_file(token_path)
                    service = build("calendar", "v3", credentials=creds)

                    # Verificar conflitos
                    eventos = service.events().list(
                        calendarId='primary',
                        timeMin=inicio.isoformat(),
                        timeMax=fim.isoformat(),
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()

                    if eventos.get('items'):
                        enviar_mensagem(numero, "⚠️ Este horário já está ocupado. Escolha outro horário disponível.")
                        return HttpResponse(status=200)

                    evento = {
                        'summary': f'Consulta da paciente {nome}',
                        'description': f'Agendado via WhatsApp por {nome}',
                        'start': {'dateTime': inicio.isoformat(), 'timeZone': 'America/Sao_Paulo'},
                        'end': {'dateTime': fim.isoformat(), 'timeZone': 'America/Sao_Paulo'},
                    }

                    service.events().insert(calendarId='primary', body=evento).execute()
                    enviar_mensagem(numero, f"✅ {nome}, sua consulta foi agendada para {inicio.strftime('%d/%m/%Y')} às {inicio.strftime('%H:%M')}.")

                    conversas_usuarios.pop(numero, None)

                except ValueError:
                    enviar_mensagem(numero, "⚠️ Formato de horário inválido. Use HH:MM (ex: 14:00).")
            else:
                enviar_mensagem(numero, "❓ Não entendi. Envie 'consulta' para iniciar um agendamento.")
        except KeyError:
            print("Nenhuma mensagem válida encontrada.")

        return HttpResponse(status=200)

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
        "text": {"body": mensagem}
    }
    response = requests.post(url, headers=headers, json=data)
    print("Resposta do envio:", response.status_code, response.text)
