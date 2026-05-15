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
from .models import Cliente, Mensagem
from .models import Contato
from django.shortcuts import render, redirect
from .forms import ClienteForm
from django.views.decorators.http import require_POST
from django.db.models import Max
from django.utils import timezone
from django.core.files.base import ContentFile
import subprocess
import tempfile
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from dotenv import load_dotenv
from pathlib import Path
from django.contrib.auth.decorators import login_required
from .decorators import super_admin_required
from .models import RegraBot
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from .models import Empresa, UsuarioEmpresa, Agendamento
from .forms import UsuarioEmpresaForm
from .models import EtapaBot, OpcaoBot,FluxoBot, ConexaoEtapa
from .google_calendar import (listar_horarios_disponiveis,criar_evento_google)



BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


# Armazena o estado da conversa por número
conversas_usuarios = {}

# Token para verificação do webhook Meta
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")


def home(request):

    if request.user.is_authenticated:
        return redirect('painel')

    return redirect('login')


def tela_inicial(request):
    return render(request, 'tela_inicial.html')


def painel(request):
    contatos = Contato.objects.all().order_by('-ultima_mensagem_em')

    return render(request, 'chat/painel.html', {
        'contatos': contatos,
        'mensagens': None,
        'numero_atual': None
    })

def painel_chat_numero(request, numero):

     # 🔥 ZERA BADGE AO ABRIR CONVERSA
    Contato.objects.filter(numero=numero).update(
        nao_lidas=0
    )

    contatos = Contato.objects.all().order_by('-ultima_mensagem_em')

    mensagens = Mensagem.objects.filter(numero=numero).order_by('data_hora')

    # 🔥 NOVO: busca o contato atual
    contato = Contato.objects.filter(numero=numero).first()

    return render(request, 'chat/painel.html', {
        'contatos': contatos,
        'mensagens': mensagens,
        'numero_atual': numero,
        'contato': contato  # 👈 ADICIONADO
    })



@csrf_exempt
def webhook(request):

    if request.method == "GET":
        verify_token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if verify_token == VERIFY_TOKEN:
            return HttpResponse(challenge)
        return HttpResponse("Token inválido", status=403)

    elif request.method == "POST":

        data = json.loads(request.body.decode("utf-8"))

        try:
            from .models import (
                Contato, Mensagem, Empresa, Cliente,
                EtapaBot, ConexaoEtapa, OpcaoBot
            )

            for entry in data.get('entry', []):
                for change in entry.get('changes', []):

                    value = change.get('value', {})
                    phone_number_id = value.get('metadata', {}).get('phone_number_id')

                    empresa = Empresa.objects.filter(
                        whatsapp_phone_number_id=phone_number_id
                    ).first()

                    if not empresa:
                        continue

                    messages = value.get('messages', [])
                    statuses = value.get("statuses", [])

                    # =========================
                    # STATUS DAS MENSAGENS
                    # =========================
                    for status in statuses:
                        msg_id = status.get("id")
                        status_msg = status.get("status")
                        if msg_id:
                            Mensagem.objects.filter(
                                whatsapp_id=msg_id
                            ).update(status=status_msg)

                    # =========================
                    # MENSAGENS RECEBIDAS
                    # =========================
                    for message in messages:

                        numero = message.get('from')
                        tipo = message.get('type')
                        numero = "".join(ch for ch in numero if ch.isdigit())

                        contato, _ = Contato.objects.get_or_create(
                            empresa=empresa,
                            numero=numero
                        )

                        cliente, _ = Cliente.objects.get_or_create(
                            telefone=numero
                        )

                        texto = ""
                        if tipo == 'text':
                            texto = message.get('text', {}).get('body', '').strip()

                        texto_recebido = texto.lower().strip()

                        # =========================
                        # SALVAR MENSAGEM
                        # =========================
                        Mensagem.objects.create(
                            empresa=empresa,
                            numero=numero,
                            texto=texto,
                            tipo=tipo,
                            recebida=True
                        )

                        # =========================
                        # PEGAR ETAPA ATUAL
                        # =========================
                        etapa = contato.etapa_atual

                        # =========================
                        # VOLTAR AO MENU
                        # =========================
                        if texto_recebido in ["menu", "cancelar", "sair", "voltar"]:

                            contato.aguardando_data = False
                            contato.aguardando_horario = False
                            contato.data_temp = None

                            etapa_inicial = EtapaBot.objects.filter(
                                fluxo__empresa=empresa,
                                eh_inicial=True
                            ).first()

                            contato.etapa_atual = etapa_inicial
                            contato.save()

                            if etapa_inicial:
                                mensagem = etapa_inicial.mensagem
                                opcoes = OpcaoBot.objects.filter(etapa=etapa_inicial)
                                if opcoes.exists():
                                    mensagem += "\n\n"
                                    for op in opcoes:
                                        mensagem += f"{op.texto_opcao}\n"
                                enviar_mensagem(empresa, cliente, numero, mensagem)

                            continue

                        # =========================
                        # ATENDIMENTO HUMANO
                        # =========================
                        if contato.em_atendimento_humano:

                            if contato.ultimo_atendimento:
                                limite = timezone.now() - timedelta(minutes=30)
                                if contato.ultimo_atendimento < limite:
                                    contato.em_atendimento_humano = False
                                    etapa_inicial = EtapaBot.objects.filter(
                                        fluxo__empresa=empresa,
                                        eh_inicial=True
                                    ).first()
                                    contato.etapa_atual = etapa_inicial
                                    contato.save()
                                    if etapa_inicial:
                                        mensagem = etapa_inicial.mensagem
                                        opcoes = OpcaoBot.objects.filter(etapa=etapa_inicial)
                                        if opcoes.exists():
                                            mensagem += "\n\n"
                                            for op in opcoes:
                                                mensagem += f"{op.texto_opcao}\n"
                                        enviar_mensagem(empresa, cliente, numero, mensagem)
                                    continue

                            contato.ultimo_atendimento = timezone.now()
                            contato.save()
                            continue

                        # =========================
                        # INICIAR FLUXO
                        # =========================
                        if not etapa:

                            etapa_inicial = EtapaBot.objects.filter(
                                fluxo__empresa=empresa,
                                eh_inicial=True
                            ).first()

                            if not etapa_inicial:
                                continue

                            contato.etapa_atual = etapa_inicial
                            contato.save()

                            mensagem = etapa_inicial.mensagem
                            opcoes = OpcaoBot.objects.filter(etapa=etapa_inicial)
                            if opcoes.exists():
                                mensagem += "\n\n"
                                for op in opcoes:
                                    mensagem += f"{op.texto_opcao}\n"

                            enviar_mensagem(empresa, cliente, numero, mensagem)
                            continue

                        # =========================
                        # RECEBER DATA
                        # =========================
                        if contato.aguardando_data:
                            try:
                                from datetime import datetime
                                data_obj = datetime.strptime(
                                    texto_recebido, "%d/%m/%Y"
                                ).date()
                                contato.data_temp = str(data_obj)
                                contato.aguardando_data = False
                                contato.aguardando_horario = True
                                contato.save()

                                from .google_calendar import listar_horarios_disponiveis
                                horarios = listar_horarios_disponiveis(data_obj)

                                if not horarios:
                                    enviar_mensagem(empresa, cliente, numero,
                                        "❌ Não há horários disponíveis nesta data.")
                                    continue

                                msg = "🕐 Horários disponíveis:\n\n"
                                for h in horarios:
                                    msg += f"{h}\n"
                                enviar_mensagem(empresa, cliente, numero, msg)
                                continue

                            except:
                                enviar_mensagem(empresa, cliente, numero,
                                    "❌ Data inválida.\n\nUse:\n13/05/2026")
                                continue

                        # =========================
                        # RECEBER HORÁRIO
                        # =========================
                        if contato.aguardando_horario:
                            horario = texto.strip()
                            try:
                                from datetime import datetime
                                from .google_calendar import (
                                    listar_horarios_disponiveis,
                                    criar_evento_google
                                )
                                data_obj = datetime.strptime(
                                    contato.data_temp, "%Y-%m-%d"
                                ).date()
                                horarios_disponiveis = listar_horarios_disponiveis(data_obj)

                                if horario not in horarios_disponiveis:
                                    enviar_mensagem(empresa, cliente, numero,
                                        "❌ Horário inválido.\n\nEscolha um horário da lista.")
                                    continue

                                data_hora = datetime.strptime(
                                    f"{contato.data_temp} {horario}", "%Y-%m-%d %H:%M"
                                )
                                criar_evento_google(
                                    nome=contato.nome or numero,
                                    telefone=numero,
                                    inicio=data_hora
                                )
                                Agendamento.objects.create(
                                    empresa=empresa,
                                    nome=contato.nome or numero,
                                    telefone=numero,
                                    horario=data_hora,
                                    confirmado=True
                                )
                                contato.aguardando_horario = False
                                contato.data_temp = None

                                etapa_inicial = EtapaBot.objects.filter(
                                    fluxo__empresa=empresa,
                                    eh_inicial=True
                                ).first()
                                contato.etapa_atual = etapa_inicial
                                contato.save()

                                mensagem = f"✅ Agendamento confirmado para {data_obj.strftime('%d/%m/%Y')} às {horario}"
                                if etapa_inicial:
                                    mensagem += "\n\n" + etapa_inicial.mensagem
                                    opcoes = OpcaoBot.objects.filter(etapa=etapa_inicial)
                                    if opcoes.exists():
                                        mensagem += "\n\n"
                                        for op in opcoes:
                                            mensagem += f"{op.texto_opcao}\n"

                                enviar_mensagem(empresa, cliente, numero, mensagem)
                                continue

                            except Exception as e:
                                print("ERRO AGENDAMENTO:", e)
                                enviar_mensagem(empresa, cliente, numero,
                                    "❌ Erro ao processar agendamento.")
                                continue

                        # =========================
                        # AGENDAMENTO - PEDIR DATA
                        # =========================
                        if (
                            etapa
                            and etapa.nome.lower() == "agendamento"
                            and texto_recebido == "1"
                        ):
                            contato.aguardando_data = True
                            contato.aguardando_horario = False
                            contato.save()
                            enviar_mensagem(empresa, cliente, numero,
                                "📅 Qual data deseja agendar?\n\nExemplo:\n13/05/2026")
                            continue

                        # =========================
                        # PROCURAR OPÇÃO
                        # =========================
                        opcao = None
                        opcoes_etapa = OpcaoBot.objects.filter(etapa=etapa)

                        for op in opcoes_etapa:
                            chave = op.texto_opcao.lower().strip().split("-")[0].strip()
                            if texto_recebido == chave:
                                opcao = op
                                break

                        if opcao and opcao.proxima_etapa:

                            proxima = opcao.proxima_etapa
                            contato.etapa_atual = proxima

                            if proxima.nome.lower() == "atendimento humano":
                                contato.em_atendimento_humano = True
                                contato.ultimo_atendimento = timezone.now()

                            contato.save()

                            mensagem = proxima.mensagem
                            opcoes_proxima = OpcaoBot.objects.filter(etapa=proxima)
                            if opcoes_proxima.exists():
                                mensagem += "\n\n"
                                for op in opcoes_proxima:
                                    mensagem += f"{op.texto_opcao}\n"

                            enviar_mensagem(empresa, cliente, numero, mensagem)
                            continue

                        # =========================
                        # FALLBACK
                        # =========================
                        mensagem = etapa.mensagem
                        opcoes = OpcaoBot.objects.filter(etapa=etapa)
                        if opcoes.exists():
                            mensagem += "\n\n"
                            for op in opcoes:
                                mensagem += f"{op.texto_opcao}\n"

                        enviar_mensagem(empresa, cliente, numero, mensagem)

        except Exception as e:
            print("❌ ERRO:", e)

        return HttpResponse("EVENT_RECEIVED")

    return HttpResponse("Método não suportado", status=405)




def ping_status(request, numero):
    Contato.objects.filter(numero=numero).update(
        online=True,
        ultimo_ping=timezone.now()
    )
    return JsonResponse({"ok": True})



def typing_status(request, numero, status):
    Contato.objects.filter(numero=numero).update(
        digitando=(status == "on")
    )
    return JsonResponse({"ok": True})



def enviar_mensagem(empresa, cliente, numero_destino, mensagem):

    import requests
    from django.utils import timezone
    from .models import Mensagem, Contato

    url = f"https://graph.facebook.com/v19.0/{empresa.whatsapp_phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {empresa.whatsapp_access_token}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": mensagem}
    }

    response = requests.post(url, headers=headers, json=data)

    print("📤 Status Code:", response.status_code)

    try:
        resp_json = response.json()
        print("📤 Response JSON:", resp_json)
    except Exception:
        resp_json = {}
        print("📤 Response Text:", response.text)

    # 🔥 ID da mensagem enviada
    msg_id = None
    if "messages" in resp_json:
        msg_id = resp_json["messages"][0].get("id")

    # 🔥 SALVA NO BANCO (com empresa + cliente)
    Mensagem.objects.create(
        empresa=empresa,
        cliente=cliente,
        numero=numero_destino,
        texto=mensagem,
        recebida=False,
        status="sent",
        whatsapp_id=msg_id
    )

    # 🔥 ATUALIZA CONTATO
    Contato.objects.filter(
        empresa=empresa,
        numero=numero_destino
    ).update(
        ultima_mensagem_em=timezone.now()
    )

    print("✅ Mensagem enviada com sucesso")




def listar_clientes(request):
    clientes = Cliente.objects.all()
    return render(request, 'clientes/listar.html', {'clientes': clientes})


def novo_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('listar')
    else:
        form = ClienteForm()
    return render(request, 'clientes/novo.html', {'form': form})





def conversa(request, numero):
    mensagens = Mensagem.objects.filter(numero=numero).order_by("data_hora")
    cliente = Cliente.objects.filter(telefone=numero).first()

    return render(request, "chat/painel.html", {
        "mensagens": mensagens,
        "numero_atual": numero,
        "cliente": cliente
    })




@require_POST
def responder_mensagem(request, numero):

    from django.http import JsonResponse

    print("🔥 RECEBEU ENVIO")

    try:

        texto = request.POST.get("mensagem", "")
        arquivo = request.FILES.get("arquivo") or request.FILES.get("audio")

        # 🔥 pega contato com segurança
        contato = Contato.objects.filter(numero=numero).first()
        print("CONTATO:", contato)

        if not contato:
            return JsonResponse({
                "ok": False,
                "erro": "Contato não encontrado"
            }, status=400)

        # 🔥 agora sim pega empresa com segurança
        empresa = getattr(contato, "empresa", None)
        print("EMPRESA:", empresa)

        if not empresa:
            return JsonResponse({
                "ok": False,
                "erro": "Empresa não encontrada no contato"
            }, status=400)

        cliente = Cliente.objects.filter(
            telefone=numero
        ).first()

        tipo = "text"

        if arquivo:

            content_type = arquivo.content_type

            if content_type.startswith("image"):
                tipo = "image"

            elif content_type.startswith("video"):
                tipo = "video"

            elif content_type.startswith("audio"):
                tipo = "audio"

            else:
                tipo = "document"

        # 🔥 ENVIO TEXTO
        if arquivo:

            enviar_midia_whatsapp(
                empresa,
                cliente,
                numero,
                arquivo,
                tipo,
                texto
            )

        else:

            enviar_mensagem(
                empresa,
                cliente,
                numero,
                texto
            )

        # ✅ resposta pro front (isso faz a mensagem aparecer no chat)
        return JsonResponse({
            "ok": True,
            "mensagem": {
                "texto": texto,
                "numero": numero,
                "tipo": tipo
            }
        })

    except Exception as e:

        print("❌ ERRO NO responder_mensagem:", e)

        return JsonResponse({
            "ok": False,
            "erro": str(e)
        }, status=500)



def enviar_template(empresa, numero):

    url = f"https://graph.facebook.com/v20.0/{empresa.whatsapp_phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {empresa.whatsapp_access_token}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "template",
        "template": {
            "name": "boas_vindas_simples",
            "language": {
                "code": "pt_BR"
            }
        }
    }

    response = requests.post(url, headers=headers, json=data)

    print("Status Code:", response.status_code)

    try:
        print("Response JSON:", response.json())
        return response.json()
    except:
        print("Response Text:", response.text)
        return {"error": response.text}







def pagina_adicionar_contato(request):
    from .forms import ContatoForm
    form = ContatoForm()
    return render(request, "contato/adicionar_contato.html", {"form": form})


@csrf_exempt
def limpar_mensagens(request, numero):
    if request.method == "POST":
        try:
            numero_limpo = "".join(ch for ch in numero if ch.isdigit())

            # 🔥 apaga apenas as mensagens
            from .models import Mensagem, Contato
            Mensagem.objects.filter(numero=numero_limpo).delete()

            # 🔥 zera badge
            Contato.objects.filter(numero=numero_limpo).update(nao_lidas=0)

            return JsonResponse({"success": True})

        except Exception as e:
            return JsonResponse({"success": False, "erro": str(e)})

    return JsonResponse({"success": False})



def baixar_midia(empresa, media_id):

    # 🔹 pega URL da mídia
    url = f"https://graph.facebook.com/v19.0/{media_id}"

    headers = {
        "Authorization": f"Bearer {empresa.whatsapp_access_token}"
    }

    res = requests.get(url, headers=headers)

    try:
        media_url = res.json().get("url")
    except:
        print("Erro ao obter URL da mídia:", res.text)
        return None

    if not media_url:
        print("URL da mídia não encontrada")
        return None

    # 🔹 baixa arquivo
    media_res = requests.get(media_url, headers=headers)

    return media_res.content


def enviar_midia_whatsapp(empresa, cliente, numero, arquivo, tipo, legenda=""):

    upload_url = f"https://graph.facebook.com/v20.0/{empresa.whatsapp_phone_number_id}/media"

    headers = {
        "Authorization": f"Bearer {empresa.whatsapp_access_token}"
    }

    # 🔥 TRATAMENTO DE ÁUDIO
    if tipo == "audio":

        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_in:
            for chunk in arquivo.chunks():
                temp_in.write(chunk)
            input_path = temp_in.name

        output_path = input_path.replace(".webm", ".ogg")

        subprocess.run([
            "ffmpeg",
            "-y",
            "-i", input_path,

            "-vn",
            "-map_metadata", "-1",

            "-acodec", "libopus",
            "-b:a", "16k",
            "-ar", "16000",
            "-ac", "1",

            "-application", "voip",
            "-frame_duration", "20",

            "-f", "ogg",
            output_path
        ])

        arquivo_final = open(output_path, "rb")

        files = {
            "file": ("audio.ogg", arquivo_final, "audio/ogg")
        }

    else:
        arquivo.seek(0)

        files = {
            "file": (arquivo.name, arquivo, arquivo.content_type)
        }

    data = {
        "messaging_product": "whatsapp"
    }

    # 🔥 UPLOAD
    upload_response = requests.post(
        upload_url,
        headers=headers,
        files=files,
        data=data
    )

    print("UPLOAD RESPONSE:", upload_response.json())

    media_id = upload_response.json().get("id")

    if not media_id:
        print("❌ ERRO: media_id não veio")
        return

    # 🔥 ENVIO DA MÍDIA
    url = f"https://graph.facebook.com/v20.0/{empresa.whatsapp_phone_number_id}/messages"

    if tipo == "audio":
        payload = {
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "audio",
            "audio": {
                "id": media_id,
                "voice": True
            }
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": numero,
            "type": tipo,
            tipo: {
                "id": media_id
            }
        }

        if legenda and tipo in ["image", "video", "document"]:
            payload[tipo]["caption"] = legenda

    send_response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {empresa.whatsapp_access_token}",
            "Content-Type": "application/json"
        },
        json=payload
    )

    print("SEND RESPONSE:", send_response.json())

    # 🔥 SALVAR NO BANCO
    try:

        resp_json = send_response.json()

        msg_id = None

        if "messages" in resp_json:
            msg_id = resp_json["messages"][0].get("id")

        Mensagem.objects.create(
            empresa=empresa,
            cliente=cliente,
            numero=numero,
            texto=legenda or f"[{tipo}]",
            arquivo=arquivo,
            tipo=tipo,
            recebida=False,
            status="sent",
            whatsapp_id=msg_id
        )

        # 🔥 ATUALIZA CONTATO
        Contato.objects.filter(
            empresa=empresa,
            numero=numero
        ).update(
            ultima_mensagem_em=timezone.now()
        )

    except Exception as e:
        print("❌ ERRO AO SALVAR MENSAGEM:", e)




def tela_adicionar_contato(request):
    return render(request, "contato/adicionar_contato.html")


@require_POST
def adicionar_contato(request):

    nome = (request.POST.get("nome") or "").strip()
    numero = (request.POST.get("numero") or "").strip()

    if not numero:
        return redirect("painel")

    numero = "".join(ch for ch in numero if ch.isdigit())

    # 🔥 empresa via relação UsuarioEmpresa (CORRIGIDO)
    empresa_rel = getattr(request.user, "usuarioempresa", None)

    if not empresa_rel:
        return JsonResponse({
            "ok": False,
            "erro": "Usuário sem vínculo com empresa"
        }, status=400)

    empresa = empresa_rel.empresa

    # 🔥 salva cliente
    cliente, _ = Cliente.objects.get_or_create(telefone=numero)

    # 🔥 cria ou atualiza contato (AGORA SEM RISCO)
    contato, created = Contato.objects.get_or_create(
        empresa=empresa,
        numero=numero
    )

    # 🔥 salva nome se vier
    if nome:
        contato.nome = nome
        contato.save()

    # 🔥 ENVIA TEMPLATE
    enviar_template(
        empresa,
        numero
    )

    return redirect("painel_chat_numero", numero=numero)



def contatos_lista(request):
    contatos = Contato.objects.all().order_by('-ultima_mensagem_em')

    return render(request, 'contato/lista.html', {
        'contatos': contatos
    })


@require_http_methods(["GET", "POST"])
def editar_contato(request, id):
    contato = get_object_or_404(Contato, id=id)

    if request.method == "POST":
        nome = request.POST.get("nome")
        numero = request.POST.get("numero")

        if numero:
            numero = "".join(ch for ch in numero if ch.isdigit())
            contato.numero = numero

        contato.nome = nome
        contato.save()

        return redirect('contatos_lista')

    return render(request, 'contato/editar.html', {
        'contato': contato
    })


@csrf_exempt
def deletar_contato(request, numero):
    if request.method == "POST":
        try:
            numero_limpo = numero.replace("+", "").strip()

            # Apaga mensagens
            Mensagem.objects.filter(numero__icontains=numero_limpo).delete()

            # Apaga contato
            Contato.objects.filter(numero__icontains=numero_limpo).delete()

            return JsonResponse({"success": True})

        except Exception as e:
            return JsonResponse({"success": False, "erro": str(e)})

    return JsonResponse({"success": False})


@login_required
def configurar_empresa(request):

    empresa = request.user.empresa

    if request.method == "POST":

        empresa.verify_token = request.POST.get("verify_token")
        empresa.whatsapp_access_token = request.POST.get("whatsapp_access_token")
        empresa.whatsapp_phone_number_id = request.POST.get("whatsapp_phone_number_id")
        empresa.google_calendar_id = request.POST.get("google_calendar_id")

        empresa.horario_inicio = request.POST.get("horario_inicio")
        empresa.horario_fim = request.POST.get("horario_fim")

        empresa.save()

        return redirect("configurar_empresa")

    return render(request, "chat/configurar_empresa.html", {
        "empresa": empresa
    })



@super_admin_required
def painel_saas(request):

    empresas = Empresa.objects.all().order_by("-id")

    total_empresas = empresas.count()

    return render(request, "saas/painel_saas.html", {
        "empresas": empresas,
        "total_empresas": total_empresas
    })

@super_admin_required
def editar_empresa(request, id):

    empresa = Empresa.objects.get(id=id)

    if request.method == "POST":

        empresa.nome = request.POST.get("nome")
        empresa.verify_token = request.POST.get("verify_token")
        empresa.whatsapp_access_token = request.POST.get("whatsapp_access_token")
        empresa.whatsapp_phone_number_id = request.POST.get("whatsapp_phone_number_id")
        empresa.google_calendar_id = request.POST.get("google_calendar_id")

        empresa.save()

        return redirect("painel_saas")

    return render(request, "saas/editar_empresa.html", {
        "empresa": empresa
    })


@super_admin_required
def criar_empresa(request):

    if request.method == "POST":

        Empresa.objects.create(
            nome=request.POST.get("nome"),
            verify_token=request.POST.get("verify_token"),
            whatsapp_access_token=request.POST.get("whatsapp_access_token"),
            whatsapp_phone_number_id=request.POST.get("whatsapp_phone_number_id"),
            google_calendar_id=request.POST.get("google_calendar_id"),
            horario_inicio="08:00",
            horario_fim="18:00",
        )

        return redirect("painel_saas")

    return render(request, "saas/criar_empresa.html")





def regras_bot(request):

    # 🔥 segurança: evita crash se não tiver vínculo empresa
    if not hasattr(request.user, "usuarioempresa"):
        return HttpResponseForbidden("Acesso não autorizado")

    empresa = request.user.usuarioempresa.empresa

    # 🔥 cria regra
    if request.method == "POST":
        palavra = request.POST.get("palavra")
        resposta = request.POST.get("resposta")

        if palavra and resposta:
            RegraBot.objects.create(
                empresa=empresa,
                palavra_chave=palavra,
                resposta=resposta,
                ativo=True
            )

    # 🔥 lista regras da empresa logada
    regras = RegraBot.objects.filter(empresa=empresa)

    return render(request, "bot/configuracoes_bot.html", {
        "regras": regras
    })


def super_admin_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)


@super_admin_required
def criar_usuario_empresa(request):

    empresas = Empresa.objects.all()

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")
        empresa_id = request.POST.get("empresa_id")
        funcao = request.POST.get("funcao")

        empresa = Empresa.objects.get(id=empresa_id)

        # cria user
        user = User.objects.create_user(
            username=username,
            password=password
        )

        # vincula empresa
        UsuarioEmpresa.objects.create(
            user=user,
            empresa=empresa,
            funcao=funcao
        )

        return redirect("painel_saas")

    return render(request, "saas/criar_usuario.html", {
        "empresas": empresas
    })

@super_admin_required
def listar_usuarios(request):

    usuarios = UsuarioEmpresa.objects.select_related("user", "empresa").all()

    return render(request, "saas/lista_usuarios.html", {
        "usuarios": usuarios
    })


def configuracoes_bot(request):
    try:
        empresa = request.user.usuarioempresa.empresa
    except Exception:
        return redirect("login")

    fluxo, _ = FluxoBot.objects.get_or_create(
        empresa=empresa,
        nome="Fluxo Principal"
    )

    etapas = EtapaBot.objects.filter(fluxo=fluxo).prefetch_related("opcaobot_set")

    conexoes = list(
        ConexaoEtapa.objects.filter(empresa=empresa)
        .values(
                    "de_etapa_id",
                    "para_etapa_id",
                    "gatilho",
                    "opcao_id"
                )
    )

    print(f"EMPRESA ID: {empresa.id}")
    print(f"CONEXOES: {conexoes}")

    import json
    return render(request, "bot/configuracoes_bot.html", {
        "etapas": etapas,
        "conexoes": conexoes,           # ← para o {% for c in conexoes %} no template
        "conexoes_json": json.dumps(conexoes),  # ← para o JS
    })



@require_POST
def criar_etapa(request):

    try:
        empresa = request.user.usuarioempresa.empresa
    except Exception:
        return JsonResponse({
            "ok": False,
            "erro": "Usuário sem vínculo com empresa"
        }, status=400)

    fluxo, _ = FluxoBot.objects.get_or_create(
        empresa=empresa,
        nome="Fluxo Principal"
    )

    EtapaBot.objects.create(
        fluxo=fluxo,
        nome=request.POST.get("nome"),
        mensagem=request.POST.get("mensagem"),
        eh_inicial="inicial" in request.POST
    )

    return redirect("configuracoes_bot")


@require_POST
def criar_opcao(request, etapa_id):



    etapa = EtapaBot.objects.get(id=etapa_id)

    proxima = EtapaBot.objects.get(id=request.POST.get("proxima_etapa"))

    OpcaoBot.objects.create(
        etapa=etapa,
        texto_opcao=request.POST.get("texto_opcao"),
        proxima_etapa=proxima
    )

    return redirect("configuracoes_bot")


@require_POST
def salvar_posicao_etapa(request):

    try:

        data = json.loads(request.body)

        etapa_id = data.get("id")
        x = data.get("x")
        y = data.get("y")

        etapa = EtapaBot.objects.get(id=etapa_id)

        etapa.pos_x = x
        etapa.pos_y = y
        etapa.save()

        return JsonResponse({
            "ok": True
        })

    except Exception as e:

        print("ERRO SALVAR POSIÇÃO:", e)

        return JsonResponse({
            "ok": False
        }, status=400)



@require_POST
def salvar_conexao(request):
    import json

    try:
        data = json.loads(request.body)

        empresa = request.user.usuarioempresa.empresa

        de_id = data.get("de_etapa")
        para_id = data.get("para_etapa")

        # 🔥 NOVO
        opcao_id = data.get("opcao_id")

        print(
            f"SALVANDO CONEXAO: "
            f"de={de_id} "
            f"para={para_id} "
            f"opcao={opcao_id} "
            f"empresa={empresa.id}"
        )

        if not de_id or not para_id:
            return JsonResponse({
                "success": False,
                "erro": "IDs faltando"
            })

        # 🔥 REMOVE conexão antiga da mesma opção
        if opcao_id:
            ConexaoEtapa.objects.filter(
                empresa=empresa,
                opcao_id=opcao_id
            ).delete()

        # 🔥 REMOVE conexão antiga do conector principal
        else:
            ConexaoEtapa.objects.filter(
                empresa=empresa,
                de_etapa_id=de_id,
                opcao__isnull=True
            ).delete()

        # 🔥 CRIA NOVA
        obj = ConexaoEtapa.objects.create(
            empresa=empresa,
            de_etapa_id=de_id,
            para_etapa_id=para_id,
            opcao_id=opcao_id if opcao_id else None
        )

        print(f"CONEXAO SALVA: id={obj.id}")

        return JsonResponse({
            "success": True,
            "id": obj.id
        })

    except Exception as e:

        print(f"ERRO SALVAR CONEXAO: {e}")

        return JsonResponse({
            "success": False,
            "erro": str(e)
        })


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def salvar_posicao(request):

    if request.method == "POST":

        data = json.loads(request.body)

        etapa_id = data.get("etapa_id")
        pos_x = data.get("x")
        pos_y = data.get("y")

        try:

            etapa = EtapaBot.objects.get(id=etapa_id)

            etapa.pos_x = pos_x
            etapa.pos_y = pos_y

            etapa.save()

            return JsonResponse({
                "success": True
            })

        except Exception as e:

            return JsonResponse({
                "success": False,
                "erro": str(e)
            })

    return JsonResponse({
        "success": False
    })

@require_POST
def apagar_etapa(request):

    data = json.loads(request.body)

    etapa_id = data.get("etapa_id")

    from .models import EtapaBot

    try:

        etapa = EtapaBot.objects.get(id=etapa_id)

        etapa.delete()

        return JsonResponse({
            "success": True
        })

    except EtapaBot.DoesNotExist:

        return JsonResponse({
            "success": False
        })

@csrf_exempt
def salvar_fluxo(request):

    if request.method != "POST":
        return JsonResponse({"ok": False, "erro": "Método inválido"})

    try:
        data = json.loads(request.body.decode("utf-8"))
        empresa = request.user.usuarioempresa.empresa
    except Exception as e:
        return JsonResponse({"ok": False, "erro": str(e)})

    fluxo = FluxoBot.objects.filter(
        empresa=empresa,
        nome="Fluxo Principal"
    ).first()

    if not fluxo:
        return JsonResponse({"ok": False, "erro": "Fluxo não existe"})

    # =========================
    # 🔥 SALVAR POSIÇÕES
    # =========================
    for e in data.get("etapas", []):
        EtapaBot.objects.filter(
            id=e["id"],
            fluxo=fluxo
        ).update(
            pos_x=e["x"],
            pos_y=e["y"]
        )

    # =========================
    # 🔥 SALVAR CONEXÕES
    # =========================
    ConexaoEtapa.objects.filter(
        de_etapa__fluxo=fluxo
    ).delete()

    for c in data.get("conexoes", []):

        de = EtapaBot.objects.filter(
            id=c["de"],
            fluxo=fluxo
        ).first()

        para = EtapaBot.objects.filter(
            id=c["para"],
            fluxo=fluxo
        ).first()

        if de and para:

            ConexaoEtapa.objects.create(
                empresa=empresa,
                de_etapa=de,
                para_etapa=para
            )

    return JsonResponse({"ok": True})


@require_POST
def criar_opcao_ajax(request):
    import json
    data = json.loads(request.body)
    etapa = EtapaBot.objects.get(id=data["etapa_id"])
    opcao = OpcaoBot.objects.create(
        etapa=etapa,
        texto_opcao=data.get("texto", "Nova opção")
    )
    return JsonResponse({"ok": True, "opcao_id": opcao.id})

@require_POST
def salvar_texto_opcao(request):
    import json
    data = json.loads(request.body)
    OpcaoBot.objects.filter(id=data["opcao_id"]).update(
        texto_opcao=data["texto"]
    )
    return JsonResponse({"ok": True})



@require_POST
def deletar_conexao(request):
    import json
    data = json.loads(request.body)
    empresa = request.user.usuarioempresa.empresa
    ConexaoEtapa.objects.filter(
        empresa=empresa,
        de_etapa_id=data.get("de_etapa"),
        para_etapa_id=data.get("para_etapa")
    ).delete()
    return JsonResponse({"success": True})


@require_POST
def deletar_opcao(request):
    import json
    data = json.loads(request.body)
    opcao_id = data.get("opcao_id")

    try:
        opcao = OpcaoBot.objects.get(id=opcao_id)
        etapa_id = opcao.etapa_id

        # 🔥 Remove conexão relacionada também
        ConexaoEtapa.objects.filter(de_etapa_id=etapa_id).delete()

        opcao.delete()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "erro": str(e)})


@require_POST
def salvar_etapa(request):

    import json

    try:

        data = json.loads(request.body)

        etapa_id = data.get("etapa_id")
        nome = data.get("nome")
        mensagem = data.get("mensagem")

        etapa = EtapaBot.objects.get(id=etapa_id)

        etapa.nome = nome
        etapa.mensagem = mensagem

        etapa.save()

        return JsonResponse({
            "ok": True
        })

    except Exception as e:

        return JsonResponse({
            "ok": False,
            "erro": str(e)
        })