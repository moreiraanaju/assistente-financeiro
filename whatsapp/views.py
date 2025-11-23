import json
import logging
import requests
import os
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.utils import timezone

# Imports da Main
from transactions.parser import parse_message
from transactions.serializers import TransacaoSerializer

logger = logging.getLogger(__name__)
User = get_user_model()

# Configs
EVOLUTION_API_BASE = os.environ.get("EVOLUTION_API_BASE")
EVOLUTION_INSTANCE_NAME = os.environ.get("EVOLUTION_INSTANCE_NAME")
EVOLUTION_API_TOKEN = os.environ.get("EVOLUTION_API_TOKEN")
EVOLUTION_BOT_KEY = os.environ.get("EVOLUTION_BOT_KEY")

def send_evolution_message(number, text):
    """Envia mensagem ativa para a Evolution API"""
    if not text: return

    base = (EVOLUTION_API_BASE or "").strip().rstrip('/')
    instance = (EVOLUTION_INSTANCE_NAME or "").strip()
    token = (EVOLUTION_API_TOKEN or "").strip()

    url = f"{base}/message/sendText/{instance}"
    
    headers = {
        "apikey": token,
        "Content-Type": "application/json"
    }
    
    payload = {
        "number": number,
        "text": text,  
        "delay": 1200,
        "linkPreview": False
    }
    
    print(f"\n>>> 📤 [ENVIO] Tentando enviar para: {number}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f">>> 📡 [ENVIO] Status Evolution: {response.status_code}")
        
        # Se der erro, mostra o porquê
        if response.status_code != 200 and response.status_code != 201:
            print(f">>> 📄 [ENVIO] Erro: {response.text}\n")
        else:
            print(f">>> 🚀 [SUCESSO] Mensagem entregue!\n")

    except Exception as e:
        print(f">>> ❌ [ENVIO] Erro Crítico: {e}")

@csrf_exempt
def evolution_webhook(request):
    # 1. Segurança
    api_key_received = request.headers.get("apikey") or request.GET.get("apikey")
    if EVOLUTION_BOT_KEY and api_key_received != EVOLUTION_BOT_KEY:
        return HttpResponse("Unauthorized", status=401)

    if request.method != "POST":
        return HttpResponse("Method Not Allowed", status=405)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)

    # 2. Debug da Estrutura 
    print("\n>>> 📦 [RECEBIDO] JSON Bruto (Resumido):")
    # Imprime só as chaves pra gente entender a estrutura sem poluir demais
    print(payload.keys()) 

    # 3. Extração
    data = payload.get("data", {})
    
    # Proteção contra mensagens do próprio bot (Loop Infinito)
    if data.get("key", {}).get("fromMe") == True:
        print(">>> 🛑 Mensagem ignorada (enviada por mim mesmo).")
        return HttpResponse("OK")

    # Extrai Telefone
    remote_jid = data.get("key", {}).get("remoteJid") or data.get("remoteJid")
    if not remote_jid:
        print(">>> ⚠️ Ignorado: Sem RemoteJid")
        return JsonResponse({"status": "ignored", "reason": "no_jid"})
        
    number = remote_jid.split("@")[0]

    # Extrai Texto (Tenta os 3 lugares mais comuns)
    msg_obj = data.get("message", {})
    
    text = msg_obj.get("conversation") # Texto puro
    if not text:
        text = msg_obj.get("extendedTextMessage", {}).get("text") # Texto com preview
    if not text:
        text = data.get("body") # Legado
        
    print(f">>> 🕵️ [EXTRAÇÃO] Número: {number} | Texto Encontrado: '{text}'")

    if not text:
        print(">>> ⚠️ Falha: Texto veio vazio ou None.")
        return JsonResponse({"reply": "Nenhuma mensagem válida recebida."})

    # 4. Lógica de Negócio
    parsed_data = parse_message(text)
    reply_text = ""

    if parsed_data:
        print(f">>> 💰 [PARSER] Entendido: {parsed_data}")
        
        tipo_banco = "IN" if parsed_data["tipo"] == "R" else "OUT"
        transaction_data = {
            "description": parsed_data["descricao"],
            "value": parsed_data["valor"],
            "type": tipo_banco,
            "date_transaction": timezone.now(),
        }

        serializer = TransacaoSerializer(data=transaction_data)
        if serializer.is_valid():
            user = User.objects.first()
            if user:
                serializer.save(user=user)
                reply_text = f"✅ Sucesso! {parsed_data['tipo']} de R$ {parsed_data['valor']:.2f} registrado."
                print(">>> ✅ [BANCO] Salvo com sucesso!")
            else:
                reply_text = "Erro: Sem usuário cadastrado."
        else:
            reply_text = "Erro ao salvar. Verifique o formato."
            print(f">>> ❌ [SERIALIZER] Erros: {serializer.errors}")
    else:
        reply_text = "Não entendi. Tente '15.00 almoço'."
        print(">>> ❓ [PARSER] Não entendeu o padrão.")

    # 5. Envio da Resposta
    send_evolution_message(number, reply_text)

    return HttpResponse("OK")