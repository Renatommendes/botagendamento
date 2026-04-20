from django.urls import path
from . import views
from .views import adicionar_contato, tela_inicial

urlpatterns = [
    path('clientes/', views.listar_clientes, name='listar_clientes'),
    path('clientes/novo/', views.novo_cliente, name='novo_cliente'),

    path('webhook/', views.webhook, name='webhook'),
    path('', tela_inicial, name='tela_inicial'),
    path('', views.painel_chat, name='painel_chat'),
    path('chat/<str:numero>/', views.painel_chat, name='painel_chat_numero'),
    path('responder/<str:numero>/', views.responder_mensagem, name='responder_mensagem'),
    path("adicionar-contato/", adicionar_contato, name="adicionar_contato"),
    path('painel/', views.painel, name='painel'),
]

