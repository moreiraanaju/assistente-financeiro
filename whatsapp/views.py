# whatsapp/views.py
import os
import json
import logging
import requests
from typing import Optional
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)

# ENV vars
TRANSACTION_ENDPOINT = os.environ.get("TRANSACTION_ENDPOINT", "http://web:8000/transacao/")
AI_API_URL = os.environ.get("AI_API_URL", "").strip()
AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
EVOLUTION_BOT_KEY = os.environ.get("EVOLUTION_BOT_KEY", "").strip()  # optional: validate incoming requests

def safe_trunc(s: object, limit: int = 500) -> str:
    s = str(s) if not isinstance(s, str) else s
    return s if len(s) <= limit else s[:limit] + "...(truncated)"

def call_ai_model(user_id: str, user_text: str) -> str:
    """
    Chama um modelo de IA (ex.: OpenAI Chat Completions).
    Ajuste payload se usar outro provedor.
    """
    if not AI_API_URL or not AI_API_KEY:
        # fallback simples
        return f"Recebi: {user_text} (IA indisponível no momento)."

    payload = {
        "model": "gpt-4o-mini",  # ajuste conforme sua conta
        "messages": [
            {"role": "system", "content": "Você é um assistente financeiro conciso e claro."},
            {"role": "user", "content": user_text}
        ],
        "max_tokens": 300
    }
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        r = requests.post(AI_API_URL, headers=headers, json=payload, timeout=12)
        r.raise_for_status()
        data = r.json()
        # Assumindo formato OpenAI-style:
        text = data["choices"][0]["message"]["content"]
        return text.strip()
    except Exception as e:
        logger.exception("AI API call failed")
        return f"Desculpe, não consegui gerar resposta agora. ({e})"

@csrf_exempt
def evolution_webhook(request):
    if request.method == "GET":
        return HttpResponse("OK")

    # opcional: validar Authorization header se quiser
    if EVOLUTION_BOT_KEY:
        auth = request.headers.get("Authorization", "")
        if EVOLUTION_BOT_KEY not in auth:
            return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        logger.exception("invalid json in webhook")
        return JsonResponse({"error": "invalid json"}, status=400)

    logger.info("evolution webhook payload: %s", safe_trunc(json.dumps(payload)))

    # extrair mensagens (compatível com evolution / whatsapp-like)
    messages = []
    try:
        for e in payload.get("entry", []) or []:
            for ch in e.get("changes", []) or []:
                val = ch.get("value") or {}
                for m in val.get("messages", []) or []:
                    messages.append(m)
        if not messages:
            messages = payload.get("messages") or []
        if isinstance(payload.get("message"), dict):
            messages.append(payload.get("message"))
    except Exception:
        logger.exception("error extracting messages")
        messages = []

    if not messages:
        # reply vazio aceitável
        return JsonResponse({"reply": "Não recebi mensagem."})

    msg = messages[0]
    from_number = msg.get("from") or msg.get("sender") or ""
    text_body = ""
    if isinstance(msg.get("text"), dict):
        text_body = msg["text"].get("body", "")
    else:
        text_body = msg.get("body") or str(msg.get("text") or "")

    # opcional: postar a transação em outro serviço (pode ser responsabilidade de outro time)
    try:
        requests.post(TRANSACTION_ENDPOINT, json={"usuario": from_number, "mensagem": text_body}, timeout=6)
    except Exception:
        logger.info("transacao post failed (ignored)")

    # gerar resposta via IA
    reply_text = call_ai_model(user_id=from_number, user_text=text_body)

    # retornar para o Evolution; ele enviará ao WhatsApp automaticamente
    return JsonResponse({"reply": reply_text})
