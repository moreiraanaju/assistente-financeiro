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
    headers = {"apikey": token, "Content-Type": "application/json"}
    payload = {"number": number, "text": text, "delay": 1200, "linkPreview": False}
    try:
        requests.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f">>> ❌ [ENVIO] Erro: {e}")

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

    # 2. Extração
    data = payload.get("data", {})
    if data.get("key", {}).get("fromMe") == True:
        return HttpResponse("OK")

    remote_jid = data.get("key", {}).get("remoteJid") or data.get("remoteJid")
    if not remote_jid:
        return JsonResponse({"status": "ignored", "reason": "no_jid"})
        
    number = remote_jid.split("@")[0]
    msg_obj = data.get("message", {})
    text = msg_obj.get("conversation") or msg_obj.get("extendedTextMessage", {}).get("text") or data.get("body")

    if not text:
        return JsonResponse({"reply": "Nenhuma mensagem válida recebida."})

    print(f">>> 🕵️ [EXTRAÇÃO] Texto: '{text}'")

    # =========================================================================
    # DETECÇÃO DE INTENÇÃO (CONSULTAS)
    # =========================================================================
    text_lower = text.lower()
    tipo_consulta = None
    extra_params = ""

    # Tenta identificar filtro combinado PRIMEIRO
    match_combinado = re.search(r'(?:gastei|gastos)\s+(?:com|em|no|na)?\s*(\w+) .*?(semana|m[êe]s)', text_lower)

    if match_combinado:
        categoria_detectada = match_combinado.group(1) 
        periodo_detectado = match_combinado.group(2)   
        
        tipo_consulta = "filtro_combinado"
        extra_params = f"&periodo={periodo_detectado}&categoria={categoria_detectada}"



    # ATENÇÃO: Use ELIF aqui para não sobrescrever o filtro combinado!

    elif re.search(r'\b(semana|semanal)\b', text_lower) and re.search(r'\b(ganhei|recebi|receitas|entradas)\b', text_lower):
        tipo_consulta = "receitas_semana"

    elif re.search(r'\b(hoje|do dia)\b', text_lower) and re.search(r'\b(gastei|gastos|total|despesa|saidas)\b', text_lower):
        tipo_consulta = "hoje"

    elif re.search(r'\b(semana|semanal)\b', text_lower) and re.search(r'\b(gastei|gastos|total|despesa)\b', text_lower):
        tipo_consulta = "semana"

    elif re.search(r'\b(m[êe]s|mensal)\b', text_lower) and re.search(r'\b(gastei|gastos|total|fatura)\b', text_lower):
        tipo_consulta = "despesas"

    elif re.search(r'\b(categoria|onde gastei)\b', text_lower):
        tipo_consulta = "categorias"

    elif re.search(r'\b(saldo|quanto tenho|quanto sobrou)\b', text_lower):
        tipo_consulta = "saldo"

    elif re.search(r'\b(ganhei|recebi|receitas|entradas)\b', text_lower):
        tipo_consulta = "receitas"

    # --- EXECUÇÃO DA CONSULTA ---
    if tipo_consulta:
        print(f">>>🔍 [CONSULTA] Tipo: {tipo_consulta} | Params: {extra_params}")
        try:
            base_url = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
            url_api = f"{base_url}/api/consulta/?tipo={tipo_consulta}{extra_params}"
            
            response = requests.get(url_api, timeout=5)
            dados = response.json()

            if response.status_code == 200:
                if tipo_consulta == "filtro_combinado":
                    valor = dados.get("valor", 0.0)
                    cat_nome = dados.get("categoria", "essa categoria").capitalize()
                    periodo_txt = "nesta semana" if "semana" in extra_params else "neste mês"
                    reply_text = f"🔎 Gastos com *{cat_nome}* {periodo_txt}: R$ {valor:.2f}"
                
                elif tipo_consulta == "categorias":
                    lista = dados.get("dados", [])
                    if not lista: reply_text = "🤷‍♂️ Sem gastos por categoria no período."
                    else:
                        items = [f"▫️ {i['categoria']}: R$ {i['valor']:.2f}" for i in lista]
                        reply_text = "📊 *Gastos por Categoria:*\n" + "\n".join(items)
                else:
                    valor = dados.get("valor", 0.0)
                    titulos = {
                        "saldo": "💰 *Saldo Atual:*",
                        "hoje": "📅 *Hoje:*",
                        "semana": "🗓️ *Semana:*",
                        "despesas": "📉 *Mês:*",
                        "receitas": "📈 *Receitas:*",
                        "receitas_semana": "🤑 *Receitas (Semana):*"
                    }
                    reply_text = f"{titulos.get(tipo_consulta, 'Consulta:')} R$ {valor:.2f}"
            else:
                reply_text = f"⚠️ Erro na API: {dados.get('error')}"

        except Exception as e:
            print(f">>> ❌ Erro: {e}")
            reply_text = "Erro ao consultar dados."

        send_evolution_message(number, reply_text)
        return HttpResponse("OK")

    # =========================================================================
    # LÓGICA DE CADASTRO (CRIAR TRANSAÇÃO)
    # =========================================================================
    
    parsed_data = parse_message(text)
    reply_text = ""

    if parsed_data:
        print(f">>> 💰 [PARSER] Entendido: {parsed_data}")

        categoria = None
        if parsed_data.get("categoria_texto"):
            categoria = Category.objects.filter(name__iexact=parsed_data["categoria_texto"]).first()
        if not categoria:
            categoria = identificar_categoria(parsed_data["descricao"])
        if not categoria:
            categoria = Category.objects.filter(name="Outros").first()

        tipo_banco = "IN" if parsed_data["tipo"] == "R" else "OUT"
        
        transaction_data = {
            "description": parsed_data["descricao"],
            "value": parsed_data["valor"],
            "type": tipo_banco,
            "date_transaction": timezone.now(),
            "category": categoria.id if categoria else None
        }

        serializer = TransacaoSerializer(data=transaction_data)
        
        if serializer.is_valid():
            user = User.objects.first()
            if user:
                serializer.save(user=user)
                cat_nome = categoria.name if categoria else "Outros"
                reply_text = f"✅ Salvo em *{cat_nome}*! \nValor: R$ {parsed_data['valor']:.2f}"
            else:
                reply_text = "Erro: Sem usuário cadastrado."
        else:
            reply_text = "Erro ao salvar. Verifique o formato."
            print(f">>> ❌ [SERIALIZER] Erros: {serializer.errors}")
    else:
        # Não entendeu nada (nem consulta, nem transação)
        # return HttpResponse("OK") silencioso ou mande msg de ajuda
        pass

    if reply_text:
        send_evolution_message(number, reply_text)

    return HttpResponse("OK")