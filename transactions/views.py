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
from .services import identificar_categoria, resolver_nome_categoria
from django.db.models import Sum
from datetime import timedelta

# Aqui controlamos a API REST
User = get_user_model()

class WebhookTransactionView(APIView):
    permission_classes = [] 

    def post(self, request):
        # 1. RECEBIMENTO
        data = request.data
        text_message = data.get("body") or data.get("message") 

        if not text_message:
            return Response(
                {"error": "Campo 'body' ou 'message' ausente no JSON."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. PARSER
        parsed_data = parse_message(text_message)

        if not parsed_data:
            return Response({
                "reply": "Desculpe, não entendi. Tente algo como: '+15.50 almoço alimentação' ou '-50 gasolina transporte'."
            }, status=status.HTTP_200_OK)

        # 3. ADAPTER
        tipo_banco = "IN" if parsed_data["tipo"] == "R" else "OUT"

        categoria = None
        if parsed_data.get("categoria_texto"):
            categoria = Category.objects.filter(name__iexact=parsed_data["categoria_texto"]).first()
        if not categoria:
            categoria = identificar_categoria(parsed_data["descricao"])
        if not categoria:
            categoria = Category.objects.filter(name="Outros").first()

        transaction_data = {
            "description": parsed_data["descricao"],
            "value": parsed_data["valor"],
            "type": tipo_banco,
            "date_transaction": timezone.now(),
            "category": categoria.id if categoria else None
        }

        # 4. SALVAMENTO
        serializer = TransacaoSerializer(data=transaction_data)

        if serializer.is_valid():
            usuario_padrao = User.objects.first()
            if not usuario_padrao:
                return Response({"error": "Nenhum usuário no banco."}, status=500)

            serializer.save(user=usuario_padrao)

            # 5. RESPOSTA
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

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TransactionCreateView(generics.CreateAPIView):
    queryset = Transacao.objects.all()
    serializer_class = TransacaoSerializer

    def perform_create(self, serializer):
        descricao = self.request.data.get("description", "")
        categoria = identificar_categoria(descricao)
        serializer.save(category=categoria)


class ConsultaView(APIView):
    """
    Endpoint para consultar saldo e gastos via SQL puro.
    """

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

    SQL_HOJE = """
        SELECT SUM(value) AS total_hoje
        FROM public.transactions_transacao
        WHERE type = 'OUT'
          AND date_transaction::date = CURRENT_DATE
          AND user_id = %s;
    """

    SQL_SEMANA = """
        SELECT SUM(value) AS total_semana
        FROM public.transactions_transacao
        WHERE type = 'OUT'
        AND date_trunc('week', date_transaction) = date_trunc('week', CURRENT_DATE)
        AND user_id = %s;
    """
       
    # Consultas Combinadas (Categoria + Tempo)
    SQL_CATEGORIA_SEMANA = """
        SELECT SUM(value) 
        FROM public.transactions_transacao 
        WHERE type = 'OUT' 
          AND category_id = %s 
          AND date_transaction >= NOW() - INTERVAL '7 days'
          AND user_id = %s;
    """

    SQL_CATEGORIA_MES = """
        SELECT SUM(value) 
        FROM public.transactions_transacao 
        WHERE type = 'OUT' 
          AND category_id = %s
          AND date_transaction >= NOW() - INTERVAL '30 days'
          AND user_id = %s;
    """

    SQL_RECEITAS_SEMANA = """
        SELECT SUM(value) AS total_receitas_semana
        FROM public.transactions_transacao
        WHERE type = 'IN'
          AND date_transaction >= NOW() - INTERVAL '7 days'
          AND user_id = %s;
    """

    def get(self, request):
        tipo = request.query_params.get("tipo")
        categoria_input = request.query_params.get("categoria") 
        
        usuario = User.objects.first()
        if not usuario:
            return Response({"error": "Nenhum usuário cadastrado"}, status=500)
        user_id = usuario.id

        if not tipo:
             return Response({"error": "Parâmetro 'tipo' é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        tipo = tipo.lower()
        query = ""
        params = [user_id] 
        is_list_result = False 
        
        # Valor padrão caso não entre no filtro combinado
        categoria_exibicao = categoria_input 

        if tipo == "filtro_combinado":
            periodo = request.query_params.get("periodo")
            
            if not categoria_input or not periodo:
                return Response({"error": "Faltou categoria ou periodo"}, status=400)

            # --- INTELIGÊNCIA: Corrige 'aimentação' -> 'Alimentação' ---
            nome_correto = resolver_nome_categoria(categoria_input)
            nome_busca = nome_correto if nome_correto else categoria_input

            categoria_obj = Category.objects.filter(name__iexact=nome_busca).first()
        
            if not categoria_obj:
                # CORREÇÃO 1: Indentação arrumada (tem que estar dentro do if)
                return Response({
                    "tipo": tipo,
                    "valor": 0.0,
                    "categoria": f"'{nome_busca}' não encontrada"
                })

            # CORREÇÃO 2: Atualizamos a variável para exibir o nome oficial (ex: "Lazer")
            categoria_exibicao = categoria_obj.name 

            params = [categoria_obj.id, user_id]

            print(f">>> 🆔 Consulta: ID {categoria_obj.id} ({categoria_obj.name}) | Periodo: {periodo}")

            if "semana" in periodo:
                query = self.SQL_CATEGORIA_SEMANA
            elif "mês" in periodo or "mes" in periodo:
                query = self.SQL_CATEGORIA_MES
            else:
                 return Response({"error": "Período inválido"}, status=400)

        elif tipo == "saldo":
            query = self.SQL_SALDO
        elif tipo == "despesas":
            query = self.SQL_DESPESAS
        elif tipo == "receitas":
            query = self.SQL_RECEITAS
        elif tipo == "receitas_semana":
            query = self.SQL_RECEITAS_SEMANA
        elif tipo == "hoje":            
            query = self.SQL_HOJE
        elif tipo == "semana":        
            query = self.SQL_SEMANA
        elif tipo == "categorias":
            query = self.SQL_CATEGORIAS
            is_list_result = True
        else:
            return Response({"error": "Tipo inválido"}, status=status.HTTP_400_BAD_REQUEST)

        # Execução
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                
                if is_list_result:
                    rows = cursor.fetchall()
                    resultado = [{"categoria": row[0], "valor": float(row[1])} for row in rows]
                    return Response({"tipo": tipo, "dados": resultado})
                else:
                    row = cursor.fetchone()
                    valor = row[0] if row and row[0] is not None else 0.0
                    
                    return Response({
                        "tipo": tipo, 
                        "valor": float(valor),
                        # Agora essa variável terá o valor correto (ex: "Lazer") se passou pelo filtro
                        "categoria": categoria_exibicao 
                    })

        except Exception as e:
            print(f">>> ❌ Erro no SQL/Python: {str(e)}")
            return Response({"error": "Erro ao processar consulta", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)