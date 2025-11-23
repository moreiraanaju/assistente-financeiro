import json
import logging
import requests
import os
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.utils import timezone
from transactions.parser import parse_message
from transactions.serializers import TransacaoSerializer

logger = logging.getLogger(__name__)
User = get_user_model()

# Configs do .env
EVOLUTION_API_TOKEN = os.environ.get("EVOLUTION_API_TOKEN")
EVOLUTION_INSTANCE_NAME = os.environ.get("EVOLUTION_INSTANCE_NAME")
EVOLUTION_API_BASE = os.environ.get("EVOLUTION_API_BASE") 
EVOLUTION_BOT_KEY = os.environ.get("EVOLUTION_BOT_KEY") 

def send_evolution_message(number, text):
    """Envia mensagem ativa para a Evolution API"""
    if not text:
        return

    url = f"{EVOLUTION_API_BASE}/message/sendText/{EVOLUTION_INSTANCE_NAME}"
    headers = {
        "apikey": EVOLUTION_API_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "number": number,
        "options": {"delay": 1200, "presence": "composing"},
        "textMessage": {"text": text}
    }
    
    try:
        requests.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        logger.error(f"Falha ao enviar msg para Evolution: {e}")

@csrf_exempt
def evolution_webhook(request):

    # 1. Validação de Segurança (Basic Auth ou Token na URL/Header)
    # A Evolution pode mandar o token no header ou query params, ajuste conforme sua config
    api_key_received = request.headers.get("apikey") or request.GET.get("apikey")
    
    # Se configurou chave, valida. Se não, deixa passar (dev mode)
    if EVOLUTION_BOT_KEY and api_key_received != EVOLUTION_BOT_KEY:
        # Tenta checar se veio no payload (algumas versões mandam diferente)
        return HttpResponse("Unauthorized", status=401)

    if request.method != "POST":
        return HttpResponse("Method Not Allowed", status=405)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)

    # 2. Extração dos Dados (O "Trabalho Sujo" de limpar o JSON da Evolution)
    # Navega até achar a mensagem real
    msg_data = {}
    try:
        # Tenta estrutura padrão da Evolution/Baileys
        data = payload.get("data", {})
        if not data:
            # Fallback para estrutura estilo Meta se a Evolution estiver em modo proxy
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            data = changes.get("value", {}).get("messages", [{}])[0]

        # Pega o texto
        text = data.get("message", {}).get("conversation") or \
               data.get("message", {}).get("extendedTextMessage", {}).get("text") or \
               data.get("body") # as vezes vem direto no root

        # Pega o remetente (Remote JID)
        remote_jid = data.get("key", {}).get("remoteJid") or data.get("from")
        
        if not text or not remote_jid:
            # Pode ser status, ack, ou mensagem de mídia que ignoramos agora
            return HttpResponse("Ignored event")

        # Limpa o numero (remove @s.whatsapp.net)
        number = remote_jid.split("@")[0]

    except Exception as e:
        logger.error(f"Erro ao parsear payload: {e}")
        return HttpResponse("Payload Error", status=200) # Retorna 200 pra não travar a API

    # 3. Lógica de Negócio (Usa o que já existe em transactions!)
    reply_text = ""

    # Tenta entender se é transação
    parsed_data = parse_message(text)

    if parsed_data:
        # É uma transação! Vamos salvar.
        tipo_banco = "IN" if parsed_data["tipo"] == "R" else "OUT"
        
        transaction_data = {
            "description": parsed_data["descricao"],
            "value": parsed_data["valor"],
            "type": tipo_banco,
            "date_transaction": timezone.now(),
        }

        serializer = TransacaoSerializer(data=transaction_data)
        
        if serializer.is_valid():
            # TODO: Buscar usuario pelo telefone 'number'. Por enquanto, pegamos o primeiro.
            user = User.objects.first() 
            if user:
                serializer.save(user=user)
                reply_text = f"✅ Sucesso! {parsed_data['tipo']} de R$ {parsed_data['valor']:.2f} registrado."
            else:
                reply_text = "Erro: Usuário não identificado no sistema."
        else:
            reply_text = "Entendi que é um valor, mas houve erro ao salvar."
    else:
        # 4. Não é transação? Chama a IA (Lógica da Carol aqui)
        # Por enquanto, um echo simples para fechar a sprint
        reply_text = "Não entendi. Tente '15.00 almoço' ou '-20 uber'."

    # 5. Resposta Ativa
    send_evolution_message(number, reply_text)

    return HttpResponse("OK")