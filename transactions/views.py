from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .parser import parse_message


@csrf_exempt
def webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST"}, status=405)

    try:
        data = json.loads(request.body)
        text = data.get("body")

        if not text:
            return JsonResponse({
                "success": False,
                "message": "Corpo da mensagem ausente."
            }, status=400)

    except Exception:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    parsed = parse_message(text)

    if not parsed:
        return JsonResponse({
            "success": False,
            "message": "Formato inválido. Tente: +100 mercado ou -50 lanche."
        }, status=200)

    reply_message = (
        f"Transação {parsed['tipo']} de R$ {parsed['valor']:.2f} "
        f"registrada com sucesso! 💰"
    )

    return JsonResponse({
        "success": True,
        "reply": reply_message,
        "transaction_data": parsed
    }, status=200)
