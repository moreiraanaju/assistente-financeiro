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

    # Regex pra capturar número com sinal opcional
    match = re.search(r"([+-]?\d+(?:\.\d+)?)", original)

    if not match:
        return None

    numero_str = match.group(1)
    valor = float(numero_str)

    # Ajusta tipo baseado no sinal
    if numero_str.startswith("-"):
        valor = abs(valor)
        tipo = "D"
    elif numero_str.startswith("+"):
        tipo = "R"

    if not tipo:
        tipo = "R" if valor > 0 else "D"

    # Remove apenas o número mantendo demais partes da frase
    descricao = (original[:match.start()] + original[match.end():]).strip()
    descricao = re.sub(r"\s+", " ", descricao)  # Remove espaços duplicados

    if not descricao:
        descricao = "sem descrição"

    return {
        "valor": valor,
        "descricao": descricao,
        "tipo": tipo
    }
