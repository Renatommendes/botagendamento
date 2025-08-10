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

    # Lista de intervalos ocupados [(start, end)]
    ocupados = []
    for evento in eventos.get('items', []):
        inicio_evento = evento['start'].get('dateTime', evento['start'].get('date'))
        fim_evento = evento['end'].get('dateTime', evento['end'].get('date'))

        dt_inicio = datetime.fromisoformat(inicio_evento)
        dt_fim = datetime.fromisoformat(fim_evento)

        ocupados.append((dt_inicio, dt_fim))

    # Verifica se há sobreposição com um horário de 30 minutos
    def esta_disponivel(horario):
        fim_intervalo = horario + timedelta(minutes=30)
        for inicio, fim in ocupados:
            if inicio < fim_intervalo and fim > horario:
                return False
        return True

    # Geração dos horários disponíveis
    horarios_disponiveis = []
    horario = inicio_dia
    while horario + timedelta(minutes=30) <= fim_dia:
        if esta_disponivel(horario):
            horarios_disponiveis.append(horario.strftime("%H:%M"))
        horario += timedelta(minutes=30)

    return horarios_disponiveis
