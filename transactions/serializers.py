# os serializers permitem definir como os dados devem ser representados na saida da API
# ele basicamente converte dados de Python/Model para JSON e vice versa


from rest_framework import serializers
from .models import Category, Transacao


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class TransacaoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transacao
        fields = [
            "id",
            "user",
            "category",
            "message",
            "description",
            "date_transaction",
            "value",
            "type",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "user"]

        extra_kwargs = {
             "date_transaction": {"required": False},
             "message" :{"required" : False}
         }

    def validate_value(self, value):
        """
        Bloqueia alteração do value via serializer (além do model).
        """
        if self.instance:  # se já existe no banco
            if value != self.instance.value:
                raise serializers.ValidationError("value não pode ser alterado após criação.")
        return value






