import os
import json
import logging
import random
from groq import Groq

logger = logging.getLogger(__name__)

MODEL = "llama-3.1-8b-instant"

def _get_client():
    return Groq(api_key=os.environ.get("GROQ_API_KEY", ""))


def formatar_resumo(dados: dict) -> str | None:
    saldo = dados.get("saldo_atual", 0.0)
    receitas = dados.get("total_receitas_mes", 0.0)
    despesas = dados.get("total_despesas_mes", 0.0)
    lider = dados.get("categoria_lider") or "nenhuma"
    comparativo = dados.get("comparativo_mes_anterior")

    variacao_txt = (
        f"{comparativo:+.1f}% em relação ao mês anterior" if comparativo is not None
        else "sem dados do mês anterior para comparar"
    )

    prompt = (
        "Você é um assistente financeiro pessoal simpático. "
        "Com base nos dados abaixo, escreva um resumo financeiro curto (máximo 5 linhas), "
        "em português brasileiro informal, amigável e direto. "
        "Não use markdown, listas ou títulos — só texto corrido.\n\n"
        f"Saldo atual: R$ {saldo:.2f}\n"
        f"Receitas do mês: R$ {receitas:.2f}\n"
        f"Despesas do mês: R$ {despesas:.2f}\n"
        f"Categoria com maior gasto: {lider}\n"
        f"Variação de despesas: {variacao_txt}\n"
    )

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq formatar_resumo erro: {e}")
        print(f">>> ❌ [GROQ] Erro em formatar_resumo: {e}")
        return None


_RESPOSTAS_AFIRMATIVAS = [
    "Ótimo! 😊 Pode mandar seus gastos quando quiser.",
    "Perfeito! Estou aqui sempre que precisar. 💪",
    "Show! É só me chamar. 😄",
]

_TEXTOS_AFIRMATIVOS = {"sim", "quero sim", "quero", "ok", "certo", "entendi",
                       "obrigado", "obrigada", "valeu", "👍", "ótimo", "legal"}


def responder_mensagem_livre(text: str, dados_financeiros: dict | None = None) -> str | None:
    if text.strip().lower() in _TEXTOS_AFIRMATIVOS:
        return random.choice(_RESPOSTAS_AFIRMATIVAS)

    system_prompt = (
        "Você é o Finn, um assistente financeiro pessoal simpático e direto que opera via WhatsApp. "
        "Você ajuda usuários a registrar gastos e receitas, consultar saldo e entender seus hábitos financeiros. "
        "Responda de forma curta, amigável e em português brasileiro. "
        "Se o usuário mandar um cumprimento, cumprimente de volta e explique brevemente o que você faz. "
        "Se fizer uma pergunta sobre finanças pessoais, responda de forma útil e prática. "
        "Nunca invente dados financeiros do usuário — para consultas de saldo ou gastos, oriente a perguntar "
        "'qual meu saldo?' ou 'quanto gastei esse mês?'. Máximo de 3 linhas na resposta."
    )
    if dados_financeiros:
        saldo = dados_financeiros.get("saldo", 0.0)
        total_receitas = dados_financeiros.get("total_receitas", 0.0)
        total_despesas = dados_financeiros.get("total_despesas", 0.0)
        categoria_lider = dados_financeiros.get("categoria_lider") or "nenhuma"
        system_prompt += (
            f" Dados financeiros atuais do usuário: saldo R$ {saldo:.2f}, "
            f"receitas do mês R$ {total_receitas:.2f}, despesas do mês R$ {total_despesas:.2f}, "
            f"categoria com mais gastos: {categoria_lider}. "
            "Use esses dados para personalizar sua resposta quando relevante."
        )
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq responder_mensagem_livre erro: {e}")
        print(f">>> ❌ [GROQ] Erro em responder_mensagem_livre: {e}")
        return None


def interpretar_mensagem(text: str) -> dict | None:
    prompt = (
        "Você é um parser de mensagens financeiras em português brasileiro. "
        "A partir da mensagem abaixo, extraia as informações e retorne APENAS um JSON válido "
        "com as chaves: tipo ('R' para receita ou 'D' para despesa), valor (número float), "
        "descricao (string curta descrevendo a transação). "
        "Se não for possível identificar com clareza, retorne null.\n\n"
        f"Mensagem: \"{text}\"\n\n"
        "Resposta (apenas JSON ou null):"
    )

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()

        if raw.lower() == "null":
            return None

        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(raw)

        if not parsed.get("tipo") or parsed.get("valor") is None:
            return None

        return {
            "tipo": parsed["tipo"],
            "valor": float(parsed["valor"]),
            "descricao": parsed.get("descricao", ""),
            "categoria_texto": parsed.get("categoria_texto"),
            "confianca": "groq",
            "ambiguo": False,
        }
    except Exception as e:
        logger.error(f"Groq interpretar_mensagem erro: {e}")
        print(f">>> ❌ [GROQ] Erro em interpretar_mensagem: {e}")
        return None
