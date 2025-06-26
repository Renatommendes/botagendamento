from django.contrib import admin
from django.urls import path
from agendamentos.views import home, whatsapp_webhook

urlpatterns = [
    path('', home),  # rota inicial
    path('admin/', admin.site.urls),
    path('webhook/', whatsapp_webhook),  # seu webhook para o WhatsApp
]