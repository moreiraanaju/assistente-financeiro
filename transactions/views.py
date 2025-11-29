from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import connection
from .models import Transacao, Category  
from .serializers import TransacaoSerializer
from .parser import parse_message 
from rest_framework import generics
from .services import identificar_categoria



# Aqui controlamos a API REST, se alguém mandar um POST via Postman ou Frontend por exemplo, cai aqui


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
                "reply": "Desculpe, não entendi. Tente algo como: '+15.50 almoço alimentação' ou '-50 gasolina transporte'."
            }, status=status.HTTP_200_OK)

        # 3. ADAPTER: Converte o formato do Parser para o formato do Serializer
        tipo_banco = "IN" if parsed_data["tipo"] == "R" else "OUT"

        # Identifica categoria
        categoria = None
        if parsed_data.get("categoria_texto"):
            categoria = Category.objects.filter(name__iexact=parsed_data["categoria_texto"]).first()
        if not categoria:
            # Se categoria não veio na mensagem ou não foi encontrada, tenta identificar automaticamente
            categoria = identificar_categoria(parsed_data["descricao"])
        if not categoria:
            # Fallback: sempre ter uma categoria "Outros"
            categoria = Category.objects.filter(name="Outros").first()

        transaction_data = {
            "description": parsed_data["descricao"],
            "value": parsed_data["valor"],
            "type": tipo_banco,
            "date_transaction": timezone.now(),
            "category": categoria.id if categoria else None  # passa ID ou None
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
                f"Transação {parsed_data['tipo']} de R$ {parsed_data['valor']:.2f}"
            )
            if categoria:
                reply_message += f" salva em {categoria.name} 🚗"
            else:
                reply_message += " salva com sucesso!"

            return Response({
                "success": True,
                "reply": reply_message,
                "debug_data": serializer.data
            }, status=status.HTTP_201_CREATED)

        # Se o serializer falhar (ex: valor negativo estranho, etc)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class TransactionCreateView(generics.CreateAPIView):
    queryset = Transacao.objects.all()
    serializer_class = TransacaoSerializer

    def perform_create(self, serializer):
        descricao = self.request.data.get("description", "")  # corrigido para o campo correto do serializer
        categoria = identificar_categoria(descricao)

        serializer.save(category=categoria)


class ConsultaView(APIView):
    """
    Endpoint para consultar saldo e gastos.
    Usa queries SQL cruas (Raw SQL) definidas pela equipe de Banco.
    """

    # 1. Definindo as queries como constantes da classe (Organização)
    SQL_SALDO = """
        SELECT
            SUM(CASE WHEN type = 'IN' THEN value ELSE 0 END) -
            SUM(CASE WHEN type = 'OUT' THEN value ELSE 0 END) AS saldo_atual
        FROM public.transactions_transacao
        WHERE user_id = %s;
    """

    SQL_RECEITAS = """
        SELECT SUM(value) AS total_receitas_mes
        FROM public.transactions_transacao
        WHERE type = 'IN'
          AND EXTRACT(MONTH FROM date_transaction) = EXTRACT(MONTH FROM NOW())
          AND EXTRACT(YEAR FROM date_transaction) = EXTRACT(YEAR FROM NOW())
          AND user_id = %s;
    """

    SQL_DESPESAS = """
        SELECT SUM(value) AS total_despesas_mes
        FROM public.transactions_transacao
        WHERE type = 'OUT'
          AND EXTRACT(MONTH FROM date_transaction) = EXTRACT(MONTH FROM NOW())
          AND EXTRACT(YEAR FROM date_transaction) = EXTRACT(YEAR FROM NOW())
          AND user_id = %s;
    """

    SQL_CATEGORIAS = """
        SELECT description, SUM(value) AS gasto_total
        FROM public.transactions_transacao
        WHERE type = 'OUT'
          AND EXTRACT(MONTH FROM date_transaction) = EXTRACT(MONTH FROM NOW())
          AND EXTRACT(YEAR FROM date_transaction) = EXTRACT(YEAR FROM NOW())
          AND user_id = %s
        GROUP BY description
        ORDER BY gasto_total DESC;
    """

    def get(self, request):
        tipo = request.query_params.get("tipo") 
        
        # TODO: Em produção, pegar o ID do request.user.id. 
        # Por enquanto, mantendo fixo como nas queries originais, mas passando via código.
        user_id = 1

        if not tipo:
             return Response({"error": "Parâmetro 'tipo' é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        tipo = tipo.lower()
        query = ""
        is_list_result = False # Flag para saber se esperamos uma lista ou um valor único

        # Seleção da query
        if tipo == "saldo":
            query = self.SQL_SALDO
        elif tipo == "despesas":
            query = self.SQL_DESPESAS
        elif tipo == "receitas":
            query = self.SQL_RECEITAS
        elif tipo == "categorias":
            query = self.SQL_CATEGORIAS
            is_list_result = True
        else:
            return Response({"error": "Tipo inválido"}, status=status.HTTP_400_BAD_REQUEST)

        # Execução
        try:
            with connection.cursor() as cursor:
                # O [user_id] substitui o %s na query de forma segura
                cursor.execute(query, [user_id])
                
                if is_list_result:
                    # Para categorias, pegamos todas as linhas
                    rows = cursor.fetchall()
                    # Transforma a lista de tuplas em lista de dicionários
                    resultado = [{"categoria": row[0], "valor": float(row[1])} for row in rows]
                    return Response({"tipo": tipo, "dados": resultado})
                else:
                    # Para saldo/receitas/despesas, pegamos só um valor
                    row = cursor.fetchone()
                    valor = row[0] if row and row[0] is not None else 0.0
                    return Response({"tipo": tipo, "valor": float(valor)})

        except Exception as e:
            # Logar o erro se necessário
            return Response({"error": "Erro ao processar consulta", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)