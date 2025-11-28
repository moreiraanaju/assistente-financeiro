from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import TransacaoSerializer
from .models import Transacao
from rest_framework import status
from django.db import connection
from django.http import JsonResponse


class TransacaoCreateView(APIView):
    def criar_transacao(request):
       serializer = TransacaoSerializer(data=request.data)
       if serializer.is_valid():
           serializer.save()
           return Response({"mensagem": "Transação registrada com sucesso!"}, status=201)
       return Response({"erro": serializer.errors}, status=400)    #teste de commit


#  endpoint consulta
def consulta_view(request):      
    tipo = request.GET.get("tipo")

    if not tipo:
        return JsonResponse({"error": "Parâmetro 'tipo' é obrigatório"}, status=400)

    tipo = tipo.lower()

    if tipo == "saldo":
        valor = executar_query(carregar_sql("SALDO_TOTAL"))
    elif tipo == "hoje":
        valor = executar_query(carregar_sql("SALDO_HOJE"))
    elif tipo == "mes":
        valor = executar_query(carregar_sql("SALDO_MES"))
    else:
        return JsonResponse({"error": "Tipo inválido. Use saldo, hoje ou mes"}, status=400)

    return JsonResponse({"tipo": tipo, "valor": float(valor)})



#   integração do queries SQL
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SQL_FILE = os.path.join(BASE_DIR, "sql_queries_final.txt")


def carregar_sql(nome_query):
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        conteudo = f.read()

    blocos = conteudo.split("--")

    for bloco in blocos:
        if nome_query.upper() in bloco:
            linhas = bloco.strip().split("\n")
            linhas = [l for l in linhas if not l.strip().startswith(nome_query.upper())]
            query = "\n".join(linhas).strip()
            return query

    raise Exception(f"Query '{nome_query}' não encontrada.")


def executar_query(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        resultado = cursor.fetchone()
    return resultado[0] if resultado else 0