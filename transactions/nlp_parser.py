"""
NLP Parser - Nova interpretação de mensagens financeiras
Substitui gradualmente o parser.py com interpretação mais flexível

Formato de saída padrão:
{
    "valor": float,
    "descricao": str,
    "tipo": "R" ou "D",
    "categoria_texto": str ou None
}

VERSÃO 2.0 - Melhorias:
1. ✅ Aceita frases sem palavras-chave (mais naturais)
2. ✅ Palavras-chave expandidas por categoria
3. ✅ Linguagem natural flexível (com preposições)
4. ✅ Lógica de categoria melhorada
"""

import re


# Dicionário de categorias com palavras-chave
CATEGORIAS = {
    "alimentação": ["mercado", "supermercado", "açougue", "padaria", "restaurante", "bar", "café", "comida", "almoço", "lanche", "pizza", "hambúrguer"],
    "transporte":   ["uber", "taxi", "ônibus", "combustível", "gasolina", "passagem", "trem", "avião", "transporte"],
    "entretenimento": ["cinema", "filme", "jogo", "show", "música", "streaming", "diversão"],
    "saúde":        ["farmácia", "medicamento", "médico", "dentista", "hospital", "saúde"],
    "moradia":      ["aluguel", "luz", "água", "internet", "condomínio", "moradia"],
}

# Palavras de ação (método e tipo)
PALAVRAS_RECEITA = ["recebi", "ganhei", "entrada", "entrou", "deposito", "depósito", "transferência", "salário"]
PALAVRAS_DESPESA = ["gastei", "paguei", "comprei", "usei", "saída", "saida", "consumo", "conta"]


def interpret_message(text):
    """
    Interpreta mensagem financeira com lógica flexível (v2.0).
    
    Suporta:
    - Frases com/sem palavras-chave
    - Preposições e variações naturais
    - Sintaxe: "gastei 50 [em/no] mercado" ou só "50 mercado"
    
    Args:
        text (str): Mensagem de entrada
        
    Returns:
        dict: {valor, descricao, tipo, categoria_texto} ou None se falhar
    """
    
    if not text:
        return None
    
    original = text.strip().lower()
    original = original.replace(",", ".")
    
    # ------- 1. DETECTAR VALOR --------
    match = re.search(r"([+-]?\d+(?:\.\d+)?)", original)
    if not match:
        return None
    
    numero_str = match.group(1)
    valor = abs(float(numero_str))  # sempre positivo; o sinal vai no tipo
    
    # ------- 2. DETECTAR TIPO --------
    tipo = _detecta_tipo(original, numero_str)
    
    # ------- 3. EXTRAIR DESCRIÇÃO E CATEGORIA --------
    descricao, categoria_texto = _extrai_descricao_categoria(original, match)
    
    return {
        "valor": valor,
        "descricao": descricao,
        "tipo": tipo,
        "categoria_texto": categoria_texto
    }


def _detecta_tipo(texto, numero_str):
    """
    Detecta se é Receita (R) ou Despesa (D).
    
    Prioridade:
    1. Sinal explícito: + = Receita, - = Despesa
    2. Palavras-chave de ação
    3. Padrão: sem sinal e sem palavra-chave = Despesa
    """
    
    # Prioridade 1: Sinal explícito
    if numero_str.startswith("-"):
        return "D"
    elif numero_str.startswith("+"):
        return "R"
    
    # Prioridade 2: Palavras-chave
    for palavra in PALAVRAS_RECEITA:
        if palavra in texto:
            return "R"
    
    for palavra in PALAVRAS_DESPESA:
        if palavra in texto:
            return "D"
    
    # Padrão: Despesa por padrão
    return "D"


def _extrai_descricao_categoria(texto, match):
    """
    Extrai descrição e categoria com lógica melhorada.
    
    Estratégia:
    1. Remove número
    2. Tenta detectar categoria por palavras-chave
    3. Retira preposições (em, no, na, do, da)
    4. Define descrição e categoria
    """
    
    # Remove número
    texto_limpo = (texto[:match.start()] + texto[match.end():]).strip()
    
    # Tira espaços extras
    texto_limpo = re.sub(r"\s+", " ", texto_limpo)
    
    if not texto_limpo:
        return "sem descrição", None
    
    # ------- TENTA DETECTAR CATEGORIA --------
    categoria_encontrada = _detecta_categoria(texto_limpo)
    
    # Remove preposições comuns
    preposicoes = [" em ", " no ", " na ", " do ", " da ", " de "]
    for prep in preposicoes:
        texto_limpo = texto_limpo.replace(prep, " ")
    
    # Tira espaços extras novamente
    texto_limpo = re.sub(r"\s+", " ", texto_limpo).strip()
    
    partes = texto_limpo.split()
    
    if not partes:
        return "sem descrição", categoria_encontrada
    
    # Se achou categoria: tira as palavras-chave dela da descrição
    if categoria_encontrada:
        # Filtra palavras-chave da categoria
        palavras_categoria = set(CATEGORIAS[categoria_encontrada])
        partes_filtradas = [p for p in partes if p not in palavras_categoria]
        
        # Se sobrou algo, usa como descrição
        descricao = " ".join(partes_filtradas) if partes_filtradas else categoria_encontrada
    else:
        # Sem categoria: usa tudo como descrição
        descricao = " ".join(partes) if partes else "sem descrição"
    
    return descricao or "sem descrição", categoria_encontrada


def _detecta_categoria(texto):
    """
    Detecta categoria procurando por palavras-chave.
    
    Retorna o nome da categoria ou None.
    """
    
    for categoria, palavras in CATEGORIAS.items():
        for palavra in palavras:
            if palavra in texto:
                return categoria
    
    return None


# ========== TESTES ==========

if __name__ == "__main__":
    exemplos = [
        # Basicos
        ("gastei 50 mercado",        False),
        ("+100 salario",             False),
        ("paguei 30 uber",           False),
        # Sem palavra-chave
        ("50 mercado",               False),
        ("30 uber",                  False),
        ("15 cinema",                False),
        # Com preposicoes
        ("gastei 50 no mercado",     False),
        ("paguei 30 de uber",        False),
        ("comprei 100 no restaurante", False),
        ("recebi 200 de salario",    False),
        # Combinacoes naturais
        ("ganhei 1500 de salario",   False),
        ("usei 25 em uma pizza",     False),
        ("pagamento de 500 passagem", False),
        # Invalidos (devem retornar None)
        ("",                         True),
        ("sem numero aqui",          True),
    ]

    print("=" * 65)
    print("TESTES DO NLP PARSER")
    print("=" * 65)

    sucessos = 0
    falhas = 0

    for entrada, espera_none in exemplos:
        resultado = interpret_message(entrada)
        ok = (resultado is None) == espera_none
        status = "[OK]" if ok else "[FALHA]"

        print(f"\n{status} '{entrada}'")
        if resultado:
            sucessos += 1
            print(f"  valor={resultado['valor']}, tipo={resultado['tipo']}, cat={resultado['categoria_texto']}")
        else:
            falhas += 1

    print("\n" + "=" * 65)
    print(f"RESUMO: {sucessos} com resultado, {falhas} sem resultado (esperados)")
