import re

def parse_message(text):
    if not text:
        return None

    original = text.strip().lower()
    original = original.replace(",", ".")
    palavras_receita = ["recebi", "ganhei", "entrada", "entrou", "deposito", "depósito"]
    palavras_despesa = ["gastei", "paguei", "comprei", "usei", "saída", "saida"]

    tipo = None

    for palavra in palavras_receita:
        if palavra in original:
            tipo = "R"
            break

    if not tipo:
        for palavra in palavras_despesa:
            if palavra in original:
                tipo = "D"
                break

    # Regex para capturar número
    match = re.search(r"([+-]?\d+(?:\.\d+)?)", original)
    if not match:
        return None

    numero_str = match.group(1)
    valor = float(numero_str)


    # Ajuste de tipo com base no sinal

    # 1. Se tem sinal explícito, respeita o sinal
    if numero_str.startswith("-"):
        tipo = "D"
        valor = abs(valor)
    elif numero_str.startswith("+"):
        tipo = "R"
        
    # 2. Se não tem sinal e não achou palavras-chave (gastei/recebi)
    if not tipo:
        tipo = "D"

    # Remove só o número e mantém o resto
    texto_sem_numero = (original[:match.start()] + original[match.end():]).strip()
    texto_sem_numero = re.sub(r"\s+", " ", texto_sem_numero)

    if not texto_sem_numero:
        descricao = "sem descrição"
        categoria_texto = None
    else:
        partes = texto_sem_numero.split(" ")

        # Caso tenha mais de 1 palavra → última vira categoria
        if len(partes) >= 2:
            categoria_texto = partes[-1]
            descricao = " ".join(partes[:-1])
        else:
            descricao = partes[0]
            categoria_texto = None

    return {
        "valor": valor,
        "descricao": descricao,
        "tipo": tipo,
        "categoria_texto": categoria_texto
    }
