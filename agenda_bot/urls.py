# agenda_bot/urls.py
from django.urls import path
from agendamentos.views import whatsapp_webhook

urlpatterns = [
    path("webhook/", whatsapp_webhook),
]
