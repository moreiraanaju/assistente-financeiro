from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import TransacaoSerializer
from .models import Transacao
from rest_framework import status

class TransacaoCreateView(APIView):
    def criar_transacao(request):
       serializer = TransacaoSerializer(data=request.data)
       if serializer.is_valid():
           serializer.save()
           return Response({"mensagem": "Transação registrada com sucesso!"}, status=201)
       return Response({"erro": serializer.errors}, status=400)    #teste de commit
