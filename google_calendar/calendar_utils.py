# google_calendar/calendar_utils.py

from datetime import datetime, timedelta
import pytz
from googleapiclient.discovery import build

def buscar_horarios_disponiveis(data, creds):
    tz = pytz.timezone("America/Sao_Paulo")
    inicio_dia = tz.localize(datetime.strptime(data + " 08:00", "%Y-%m-%d %H:%M"))
    fim_dia = tz.localize(datetime.strptime(data + " 18:00", "%Y-%m-%d %H:%M"))

    service = build("calendar", "v3", credentials=creds)

    eventos = service.events().list(
        calendarId='primary',
        timeMin=inicio_dia.isoformat(),
        timeMax=fim_dia.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    ocupados = []
    for evento in eventos.get('items', []):
        inicio = evento['start'].get('dateTime', evento['start'].get('date'))
        ocupados.append(datetime.fromisoformat(inicio).time().replace(second=0, microsecond=0))

    horarios_disponiveis = []
    horario = inicio_dia
    while horario < fim_dia:
        if horario.time().replace(second=0, microsecond=0) not in ocupados:
            horarios_disponiveis.append(horario.strftime("%H:%M"))
        horario += timedelta(minutes=30)

    return horarios_disponiveis
