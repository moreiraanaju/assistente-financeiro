from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Transacao
from .serializers import TransacaoSerializer
from .parser import parse_message 
from rest_framework import generics
from .services import identificar_categoria

User = get_user_model()

class WebhookTransactionView(APIView):
    # Permite acesso sem autenticação (pois o webhook do Wpp não manda token de usuário)
    # Futuramente, validaremos um token de API no header
    permission_classes = [] 

    def post(self, request):
        # 1. RECEBIMENTO: Pega o JSON vindo do WhatsApp
        # O padrão do gustavo era esperar um campo "body"
        data = request.data
        text_message = data.get("body") or data.get("message") 

        if not text_message:
            return Response(
                {"error": "Campo 'body' ou 'message' ausente no JSON."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. PARSER: Usa a função regex do gustavo
        parsed_data = parse_message(text_message)

        if not parsed_data:
            # Se não entendeu, retorna 200 com msg de ajuda (padrão de chatbot para não ficar tentando reenvio)
            return Response({
                "reply": "Desculpe, não entendi. Tente algo como: '15.50 almoço' ou '-50 gasolina'."
            }, status=status.HTTP_200_OK)

        # 3. ADAPTER: Converte o formato do Parser para o formato do Serializer
        # Parser retorna: 'tipo' (R/D), 'valor', 'descricao'
        # Model espera: 'type' (IN/OUT), 'value', 'description'
        
        tipo_banco = "IN" if parsed_data["tipo"] == "R" else "OUT"
        
        transaction_data = {
            "description": parsed_data["descricao"],
            "value": parsed_data["valor"],
            "type": tipo_banco,
            "date_transaction": timezone.now(),
            "category": None # Por enquanto deixamos null
        }

        # 4. SALVAMENTO: Usa o Serializer para validar e salvar
        serializer = TransacaoSerializer(data=transaction_data)
        
        if serializer.is_valid():
            # Gambiarra Técnica para Testes: Pega o primeiro usuário do banco
            # TODO: Em produção, buscar o usuário pelo telefone vindo no JSON
            usuario_padrao = User.objects.first()
            if not usuario_padrao:
                return Response({"error": "Nenhum usuário no banco."}, status=500)

            serializer.save(user=usuario_padrao)

            # 5. RESPOSTA: Monta a mensagem amigável 
            reply_message = (
                f"Transação {parsed_data['tipo']} de R$ {parsed_data['valor']:.2f} "
                f"salva com sucesso! 💰"
            )
            
            return Response({
                "success": True,
                "reply": reply_message,
                "debug_data": serializer.data
            }, status=status.HTTP_201_CREATED)
        
        # Se o serializer falhar (ex: valor negativo estranho, etc)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# atualização da sprint 2 do backend
class TransactionCreateView(generics.CreateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    def perform_create(self, serializer):
        descricao = self.request.data.get("descricao", "")
        categoria = identificar_categoria(descricao)

        serializer.save(categoria=categoria)