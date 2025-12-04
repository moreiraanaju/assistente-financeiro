from unidecode import unidecode
from .models import Category
import difflib


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
        "luz", "agua", "internet", "gas", "condominio", "claro", "vivo", "net", "aluguel"
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

 
def normalizar_texto(texto: str) -> str:
    if not texto: return ""
    return unidecode(texto).lower().strip()

def resolver_nome_categoria(termo_busca: str) -> str:
    """
    Traduz 'uber' -> 'Transporte' ou corrige 'aimentação' -> 'Alimentação'
    para ser usado na consulta SQL.
    """
    termo = normalizar_texto(termo_busca)
    
    # 1. Tenta achar direto nas chaves do mapeamento (Ex: busca 'uber' acha 'Transporte')
    for categoria_oficial, palavras_chave in MAPEAMENTO.items():
        # Verifica se o termo é uma das palavras-chave (ex: 'uber')
        if termo in [normalizar_texto(p) for p in palavras_chave]:
            return categoria_oficial
        
        # Verifica se o termo é igual ao nome da categoria (ex: 'alimentacao')
        if termo == normalizar_texto(categoria_oficial):
            return categoria_oficial

    # 2. Se não achou exato, tenta corrigir erro de digitação (Fuzzy Match)
    # Pega todas as categorias oficiais + todas as palavras chave numa lista só
    todos_nomes = list(MAPEAMENTO.keys())
    match = difflib.get_close_matches(termo, [normalizar_texto(n) for n in todos_nomes], n=1, cutoff=0.7)
    
    if match:
        # Se achou algo parecido (ex: 'aimentacao'), retorna o nome correto capitalizado
        nome_encontrado = match[0]
        # Recupera o nome original (Capitalizado) baseado na chave do dict
        for key in MAPEAMENTO.keys():
            if normalizar_texto(key) == nome_encontrado:
                return key
            
    return None # Não achou nada parecido


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
