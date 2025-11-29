import json
import logging
import requests
import os
import re
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.utils import timezone
from transactions.models import Category 
from transactions.services import identificar_categoria

from transactions.parser import parse_message
from transactions.serializers import TransacaoSerializer


# Aqui controlamos o Webhook que recebe a mensagem da Evolution API

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

    # Detecção de comandos de consulta
    text_lower = text.lower() # Facilita o Regex
    tipo_consulta = None

    # 1. Regex para SALDO
    if re.search(r'\b(saldo|quanto tenho|quanto sobrou)\b', text_lower):
        tipo_consulta = "saldo"

    # 2. Regex para GASTOS DE HOJE
    elif re.search(r'\b(hoje)\b', text_lower) and re.search(r'\b(gastei|gastos|total)\b', text_lower):
        tipo_consulta = "hoje"

    # 3. Regex para GASTOS DO MÊS
    elif re.search(r'\b(m[êe]s)\b', text_lower) and re.search(r'\b(gastei|gastos|total)\b', text_lower):
        tipo_consulta = "mes"

    # 4. Regex para GASTOS POR CATEGORIA
    elif re.search(r'\b(categoria|onde gastei)\b', text_lower):
        tipo_consulta = "categorias"

    # SE FOI IDENTIFICADA UMA CONSULTA, BUSCA NO ENDPOINT E RESPONDE
    if tipo_consulta:
        print(f">>>🔍 [CONSULTA] Tipo identificado: {tipo_consulta}")
        try:
            # Chama o enpoint /consulta criado no Transactions App
            base_url = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
            url_api = f"{base_url}/api/consulta/?tipo={tipo_consulta}"
            
            response = requests.get(url_api, timeout=5)
            dados = response.json()

            if response.status_code == 200:
                # FEEDBACK
                # Por enquanto, fazemos uma formatação básica para não quebrar
                if tipo_consulta == "categorias":
                    lista_gastos = dados.get("dados", [])
                    msg_items = [f"▫️ {item['categoria']}: R$ {item['valor']:.2f}" for item in lista_gastos]
                    reply_text = "📊 *Gastos por Categoria:*\n" + "\n".join(msg_items)
                else:
                    valor = dados.get("valor", 0.0)
                    reply_text = f"💰 *Consulta {tipo_consulta.title()}:* R$ {valor:.2f}"
            else:
                reply_text = f"⚠️ Erro ao consultar: {dados.get('error')}"

        except Exception as e:
            print(f">>> ❌ [ERRO API] {e}")
            reply_text = "Desculpe, não consegui acessar seus dados agora."

        # Envia a resposta e ENCERRA a função (return) para não tentar salvar como transação
        send_evolution_message(number, reply_text)
        return HttpResponse("OK")

    # 4. Lógica de Negócio
    parsed_data = parse_message(text)
    reply_text = ""

    if parsed_data:
        print(f">>> 💰 [PARSER] Entendido: {parsed_data}")

        # --- LÓGICA DE CATEGORIA (NOVA) ---
        categoria = None
        
        # 1. Tenta pegar a categoria explicita na mensagem (ex: "transporte")
        nome_categoria_msg = parsed_data.get("categoria_texto")
        if nome_categoria_msg:
            categoria = Category.objects.filter(name__iexact=nome_categoria_msg).first()
        
        # 2. Se não achou, tenta identificar automaticamente pela descrição
        if not categoria:
            categoria = identificar_categoria(parsed_data["descricao"])

        # 3. Fallback: Se ainda assim for None, tenta "Outros"
        if not categoria:
            categoria = Category.objects.filter(name="Outros").first()
        # ----------------------------------

        tipo_banco = "IN" if parsed_data["tipo"] == "R" else "OUT"
        
        transaction_data = {
            "description": parsed_data["descricao"],
            "value": parsed_data["valor"],
            "type": tipo_banco,
            "date_transaction": timezone.now(),
            "category": categoria.id if categoria else None # Passa o ID se existir
        }

        serializer = TransacaoSerializer(data=transaction_data)
        
        if serializer.is_valid():
            user = User.objects.first() # TODO: Pegar user pelo telefone no futuro
            if user:
                serializer.save(user=user)
                
                # --- RESPOSTA DINÂMICA (NOVA) ---
                if categoria and categoria.name != "Outros":
                    reply_text = f"✅ Salvo em *{categoria.name}*! \nValor: R$ {parsed_data['valor']:.2f}"
                else:
                    reply_text = f"⚠️ Categoria não identificada. \n✅ Salvo em *Outros*: R$ {parsed_data['valor']:.2f}"
                # --------------------------------
                
                print(">>> ✅ [BANCO] Salvo com sucesso!")
            else:
                reply_text = "Erro: Sem usuário cadastrado no sistema."
        else:
            reply_text = "Erro ao salvar. Verifique o formato."
            print(f">>> ❌ [SERIALIZER] Erros: {serializer.errors}")
    else:
        reply_text = "Não entendi. Tente exemplo: '15.00 almoço'."
        print(">>> ❓ [PARSER] Não entendeu o padrão.")

    # 5. Envio da Resposta
    send_evolution_message(number, reply_text)

    return HttpResponse("OK")