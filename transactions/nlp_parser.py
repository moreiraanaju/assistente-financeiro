"""
NLP Parser - Interpretação de mensagens financeiras

Formato de saída padrão (v3.0):
{
    "valor": float | None,
    "descricao": str | None,
    "tipo": "R" | "D" | None,
    "categoria_texto": str | None,
    "confianca": "alta" | "media" | "baixa",
    "ambiguo": bool,
    "motivo_ambiguidade": str | None,
    "is_correcao": bool,
}

VERSÃO 3.0 - Melhorias:
1. ✅ Aceita frases sem palavras-chave (mais naturais)
2. ✅ Palavras-chave expandidas por categoria
3. ✅ Linguagem natural flexível (com preposições)
4. ✅ Lógica de categoria melhorada
5. ✅ Detecção de correções ("na verdade foi 30", "corrige para 45")
6. ✅ Cálculo de nível de confiança (alta / media / baixa)
7. ✅ Sinalização de ambiguidade com motivo explicado
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

# Padrões de correção — detectam mensagens que corrigem uma transação anterior
PADROES_CORRECAO = [
    # "na verdade foi 30" / "na verdade eram 50" / "na verdade 100"
    r"na verdade\s+(?:(?:foi|era|eram|foram|é|e|sao|são)\s+)?([+-]?\d+(?:\.\d+)?)",
    # "corrige para 45" / "corrija pra 15" / "corrige 50"
    r"corri(?:ge|ja?|jo)\s+(?:(?:para|pra|p)\s+)?([+-]?\d+(?:\.\d+)?)",
    # "não, foi 30" / "não era 100" / "nao foi 30"
    r"n[aã]o[,.]?\s+(?:foi|era|eram|é)\s+([+-]?\d+(?:\.\d+)?)",
]


def interpret_message(text):
    """
    Interpreta mensagem financeira com lógica flexível (v3.0).

    Suporta:
    - Frases com/sem palavras-chave
    - Preposições e variações naturais
    - Mensagens de correção ("na verdade foi 30", "corrige para 45")
    - Cálculo de confiança e sinalização de ambiguidade

    Args:
        text (str): Mensagem de entrada

    Returns:
        dict: com campos valor, tipo, descricao, categoria_texto,
              confianca, ambiguo, motivo_ambiguidade e is_correcao.
              Retorna None se a mensagem for vazia ou sem número.
    """

    if not text or not text.strip():
        return None

    original = text.strip().lower()
    original = original.replace(",", ".")

    # ------- 0. DETECTAR CORREÇÃO --------
    novo_valor = _detecta_correcao(original)
    if novo_valor is not None:
        return {
            "valor": novo_valor,
            "tipo": None,
            "descricao": None,
            "categoria_texto": None,
            "confianca": "alta",
            "ambiguo": False,
            "motivo_ambiguidade": None,
            "is_correcao": True,
        }

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

    # ------- 4. CALCULAR CONFIANÇA E AMBIGUIDADE --------
    # Descrição "real" existe se, após remover verbos de ação, sobra alguma palavra
    # OU se uma categoria foi identificada (ex: "gastei 50 mercado" → categoria alimentação)
    _VERBOS_ACAO = {
        "recebi", "ganhei", "entrou", "gastei", "paguei",
        "comprei", "usei", "saída", "saida", "consumo", "conta", "entrada",
    }
    if descricao in (None, "sem descrição", ""):
        tem_descricao = False
    else:
        palavras_reais = set(descricao.split()) - _VERBOS_ACAO
        tem_descricao = bool(palavras_reais) or (categoria_texto is not None)

    confianca, ambiguo, motivo = _calcula_confianca_e_ambiguidade(
        original, numero_str, tem_descricao
    )

    return {
        "valor": valor,
        "tipo": tipo,
        "descricao": descricao,
        "categoria_texto": categoria_texto,
        "confianca": confianca,
        "ambiguo": ambiguo,
        "motivo_ambiguidade": motivo,
        "is_correcao": False,
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


def _detecta_correcao(texto):
    """
    Verifica se a mensagem é uma correção de transação anterior.

    Padrões reconhecidos:
    - "na verdade foi 30"  /  "na verdade eram 50"  /  "na verdade 100"
    - "corrige para 80"   /  "corrija pra 15"       /  "corrige 50"
    - "não, foi 30"       /  "não era 100"

    Returns:
        float: valor corrigido, ou None se não for correção.
    """
    for padrao in PADROES_CORRECAO:
        match = re.search(padrao, texto)
        if match:
            return abs(float(match.group(1)))
    return None


def _calcula_confianca_e_ambiguidade(texto, numero_str, tem_descricao):
    """
    Calcula o nível de confiança da interpretação e se é ambígua.

    Prioridade de avaliação:
    1. Conflito de tipo (palavras de receita + despesa) → baixa, ambíguo
    2. Sinal explícito OU palavra-chave + descrição    → alta
    3. Sinal/palavra-chave presente, mas sem descrição → media, ambíguo
    4. Sem sinal/palavra, mas com descrição (padrão D) → media
    5. Só valor, sem qualquer contexto                 → baixa, ambíguo

    Returns:
        tuple: (confianca: str, ambiguo: bool, motivo: str | None)
    """
    tem_receita = any(p in texto for p in PALAVRAS_RECEITA)
    tem_despesa = any(p in texto for p in PALAVRAS_DESPESA)
    tem_sinal = numero_str.startswith(("+", "-"))
    tem_palavra_chave = tem_receita or tem_despesa

    # Conflito: palavras de receita e despesa detectadas ao mesmo tempo
    if tem_receita and tem_despesa:
        return (
            "baixa",
            True,
            "palavras de receita e despesa detectadas simultaneamente",
        )

    # Alta confiança: tipo claro (sinal ou palavra-chave) e tem descrição
    if (tem_sinal or tem_palavra_chave) and tem_descricao:
        return "alta", False, None

    # Média confiança: tipo claro mas sem descrição
    if (tem_sinal or tem_palavra_chave) and not tem_descricao:
        return "media", True, "valor identificado mas sem descrição do gasto"

    # Média confiança: sem sinal/palavra, mas tem descrição (padrão D aceitável)
    if tem_descricao:
        return "media", False, None

    # Baixa confiança: só valor, sem qualquer contexto
    return "baixa", True, "somente o valor foi informado, sem descrição ou contexto"


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
