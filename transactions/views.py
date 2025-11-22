
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .parser import parse_message

from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Transacao
from .serializers import TransacaoSerializer

# --- CÓDIGO DA BRANCH DO GUSTAVO (PARSER) ---
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

# --- CÓDIGO ANA JU ORIGINAL (SERIALIZER + DRF) ---  
# A view recebe a requisicao HTTP - chama o serializer - interage com o banco de dados via models - devolve uma resposta HTTP

User = get_user_model()

class TransacaoCreateView(APIView):

    def post(self, request):

# TODO: Implementar busca de usuário por telefone para o Bot do WhatsApp (comentario detalhado no fim da pagina)

        serializer = TransacaoSerializer(data=request.data)
        if serializer.is_valid():
            usuario = request.user  # !!! o endpoint só vai funcionar se mandar autenticação na requisição (login/senha ou token) !!!
            serializer.save(user=usuario)
            return Response({
                "mensagem": "Transação criada com sucesso!",
                "dados": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "mensagem": "Erro ao criar transação.",
            "erros": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
