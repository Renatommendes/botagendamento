from __future__ import print_function
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

import os.path
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build



SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_FILE = 'credentials.json'  # Baixe do console da Google

def criar_servico():
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('calendar', 'v3', credentials=creds)
    return service

# Teste
if __name__ == '__main__':
    servico = criar_servico()
    calendario = servico.calendarList().list().execute()
    print(calendario)


SCOPES = ['https://www.googleapis.com/auth/calendar']

def authenticate_google_account():
    creds = None
    # Verifica se já existe o token salvo
    if os.path.exists('token.json'):
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # Caso não exista, executa o fluxo OAuth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # O navegador será aberto para login na conta Google
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Salva o token
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    print("✅ Autenticado com sucesso!")
    return service

if __name__ == '__main__':
    authenticate_google_account()