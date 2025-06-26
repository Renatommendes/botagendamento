import requests

def enviar_mensagem(telefone, mensagem, token, phone_number_id):
    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "text",
        "text": {"body": mensagem}
    }

    response = requests.post(url, headers=headers, json=data)
    return response.status_code, response.text
