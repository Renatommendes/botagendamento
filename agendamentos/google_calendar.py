from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os


SCOPES = ['https://www.googleapis.com/auth/calendar']

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

SERVICE_ACCOUNT_FILE = os.path.join(
    BASE_DIR,
    'credenciais_google.json'
)

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)

service = build(
    'calendar',
    'v3',
    credentials=credentials
)

CALENDAR_ID = 'rnt.mmprojetosistema@gmail.com'


# =========================
# CRIAR EVENTO
# =========================
def criar_evento_google(nome, telefone, inicio):

    timezone_br = ZoneInfo("America/Sao_Paulo")

    inicio = inicio.replace(tzinfo=timezone_br)

    fim = inicio + timedelta(hours=1)

    evento = {
        'summary': f'Agendamento - {nome}',
        'description': f'Telefone: {telefone}',
        'start': {
            'dateTime': inicio.isoformat(),
            'timeZone': 'America/Sao_Paulo',
        },
        'end': {
            'dateTime': fim.isoformat(),
            'timeZone': 'America/Sao_Paulo',
        },
    }

    evento_criado = service.events().insert(
        calendarId=CALENDAR_ID,
        body=evento
    ).execute()

    print("✅ EVENTO CRIADO:")
    print(evento_criado)

    return evento_criado


# =========================
# HORÁRIOS DISPONÍVEIS
# =========================
def listar_horarios_disponiveis(data):

    timezone_br = ZoneInfo("America/Sao_Paulo")

    inicio_dia = datetime.combine(
        data,
        datetime.min.time()
    ).replace(
        hour=8,
        minute=0,
        tzinfo=timezone_br
    )

    fim_dia = inicio_dia.replace(hour=18)

    eventos = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=inicio_dia.isoformat(),
        timeMax=fim_dia.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    ocupados = []

    for evento in eventos.get('items', []):

        inicio_evento = evento['start'].get('dateTime')

        if inicio_evento:

            hora = datetime.fromisoformat(
                inicio_evento.replace('Z', '+00:00')
            )

            hora_local = hora.astimezone(timezone_br)

            ocupados.append(
                hora_local.strftime('%H:%M')
            )

    horarios = []

    atual = inicio_dia

    while atual < fim_dia:

        hora_txt = atual.strftime('%H:%M')

        if hora_txt not in ocupados:
            horarios.append(hora_txt)

        atual += timedelta(hours=1)

    print("HORÁRIOS OCUPADOS:", ocupados)
    print("HORÁRIOS LIVRES:", horarios)

    return horarios