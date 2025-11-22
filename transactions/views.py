# A view recebe a requisicao HTTP - chama o serializer - interage com o banco de dados via models - devolve uma resposta HTTP

from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Transacao
from .serializers import TransacaoSerializer

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


# Quando for integrar com o wpp precisa ajustar essa view para que:
# 1.Leia o JSON enviado pela API do wpp e descubra o numero de telefone
# Supondo que o JSON venha: { "phone": "5511...", "text": "gastei 50", ... }
# telefone_recebido = data.get("phone_number")

# 2. Achar o usuário dono desse telefone
#try:
#            perfil = UserProfile.objects.get(phone_number=telefone_recebido)
#             usuario_dono = perfil.user
#       except UserProfile.DoesNotExist:
#            return Response({"erro": "Telefone não cadastrado"}, status=404)

# 3. Passar os dados para o serializer
# serializer = TransacaoSerializer(data=data)

# if serializer.is_valid():
            # 4. Salva usando o usuário encontrado pelo telefone
           #serializer.save(user=usuario_dono) 
           #return Response(serializer.data, status=201)
            
    # return Response(serializer.errors, status=400)