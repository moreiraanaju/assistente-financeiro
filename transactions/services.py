from unidecode import unidecode
from .models import Category


MAPEAMENTO = {
    "Renda": [
        "salario", "pix", "deposito", "venda", "bonus"
    ],
    "Alimentação": [
        "mercado", "ifood", "restaurante", "lanche", "pizza", "padaria",
        "almoco", "jantar", "acai"
    ],
    "Transporte": [
        "uber", "99", "taxi", "onibus", "gasolina", "posto", "estacionamento"
    ],
    "Casa": [
        "luz", "agua", "internet", "gas", "condominio", "claro", "vivo", "net"
    ],
    "Saúde": [
        "farmacia", "remedio", "medico", "consulta", "exame"
    ],
    "Lazer": [
        "cinema", "bar", "viagem", "netflix", "spotify", "ingresso"
    ],
    "Compras": [
        "shopee", "amazon", "roupa", "loja", "shein", "presente"
    ],
    "Educação": [
        "faculdade", "curso", "escola", "livro", "aula"
    ],
    "Investimento": [
        "cdb", "poupanca", "tesouro", "cripto"
    ],
}

 
def normalizar_texto(texto: str) -> str:           #coloca as palavras no padrão
    return unidecode(texto).lower().strip()


def identificar_categoria(descricao: str) -> Category:
    descricao_normalizada = normalizar_texto(descricao)       
    for categoria, palavras in MAPEAMENTO.items():
        for palavra in palavras:
            if palavra in descricao_normalizada:
                try:
                    return Category.objects.get(name=categoria)
                except Category.DoesNotExist:        
                    pass 

    return Category.objects.get(name="Outros")
