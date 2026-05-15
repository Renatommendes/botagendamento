from django.urls import path
from . import views
from .views import adicionar_contato, tela_inicial,deletar_contato, editar_contato, tela_adicionar_contato, salvar_fluxo
from .views import contatos_lista
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect

urlpatterns = [
    path('clientes/', views.listar_clientes, name='listar_clientes'),
    path('clientes/novo/', views.novo_cliente, name='novo_cliente'),
    path('webhook/', views.webhook, name='webhook'),
    path('', views.home, name='home'),
    path('painel/', views.painel, name='painel'),
    path('inicio/', views.tela_inicial, name='tela_inicial'),
    # ✅ CORRIGIDO AQUI
    path('chat/<str:numero>/', views.painel_chat_numero, name='painel_chat_numero'),
    path('responder/<str:numero>/', views.responder_mensagem, name='responder_mensagem'),
    path('painel/', views.painel, name='painel'),
    path('ping/<str:numero>/', views.ping_status, name='ping_status'),
    path('typing/<str:numero>/<str:status>/', views.typing_status, name='typing_status'),
    path('novo-contato/', views.pagina_adicionar_contato, name='novo_contato'),
    path('limpar-mensagens/<str:numero>/', views.limpar_mensagens, name='limpar_mensagens'),
    path('contatos/adicionar/', tela_adicionar_contato, name='tela_adicionar_contato'),
    path("adicionar-contato/", adicionar_contato, name="adicionar_contato"),
    path('contatos/', contatos_lista, name='contatos_lista'),
    path('contatos/editar/<int:id>/', editar_contato, name='editar_contato'),
    path('contatos/deletar/<str:numero>/', deletar_contato, name='deletar_contato'),
    path('login/',auth_views.LoginView.as_view(template_name='chat/login.html'),name='login'),
    path('logout/',auth_views.LogoutView.as_view(),name='logout'),
    path('configuracao/', views.configurar_empresa, name='configurar_empresa'),
    path("saas/", views.painel_saas, name="painel_saas"),
    path("saas/empresa/<int:id>/editar/", views.editar_empresa, name="editar_empresa"),
    path("saas/criar/", views.criar_empresa, name="criar_empresa"),
    path('regras-bot/', views.regras_bot, name='regras_bot'),
    path("saas/usuarios/criar/", views.criar_usuario_empresa, name="criar_usuario_empresa"),
    path("saas/usuarios/", views.listar_usuarios, name="listar_usuarios"),
    path("bot/criar-etapa/", views.criar_etapa, name="criar_etapa"),
    path("bot/criar-opcao/<int:etapa_id>/", views.criar_opcao, name="criar_opcao"),
    path("bot/configuracoes/",views.configuracoes_bot,name="configuracoes_bot"),
    path("bot/salvar-conexao/", views.salvar_conexao, name="salvar_conexao"),
    path("bot/salvar-posicao/", views.salvar_posicao, name="salvar_posicao"),
    path("bot/apagar-etapa/", views.apagar_etapa, name="apagar_etapa"),
    path("bot/salvar-fluxo/", views.salvar_fluxo, name="salvar_fluxo"),
    path("bot/criar-opcao-ajax/", views.criar_opcao_ajax, name="criar_opcao_ajax"),
    path("bot/salvar-texto-opcao/", views.salvar_texto_opcao, name="salvar_texto_opcao"),
    path("bot/deletar-conexao/", views.deletar_conexao, name="deletar_conexao"),
    path("bot/deletar-opcao/", views.deletar_opcao, name="deletar_opcao"),
    path("bot/salvar-etapa/", views.salvar_etapa, name="salvar_etapa"),


]