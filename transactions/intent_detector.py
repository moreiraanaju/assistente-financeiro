"""
Intent Detector — Sprint 4

Responsável por classificar se uma mensagem é uma CONSULTA ou um REGISTRO.

Retorno de detect_intent():
  - dict {"tipo": str, "extra_params": dict}  → é uma consulta
  - None                                        → não é consulta; tratar como registro

Tipos de consulta reconhecidos:
  saldo             "quanto tenho?", "meu saldo", "quanto sobrou"
  despesas          gastos do mês atual
  receitas          receitas do mês atual
  receitas_semana   receitas desta semana
  hoje              gastos de hoje
  semana            gastos desta semana
  mes_passado       gastos do mês passado
  categorias        gastos agrupados por categoria
  filtro_combinado  gasto de uma categoria num período  (extra: categoria, periodo)
  historico         últimas N transações                (extra: n)
  insights          resumo financeiro geral
"""

import re
from unidecode import unidecode


def _norm(text: str) -> str:
    """Normaliza texto: minúsculas + sem acentos."""
    return unidecode(text).lower()


# ---------------------------------------------------------------------------
# Padrões de intenção — avaliados EM ORDEM (mais específico primeiro)
# ---------------------------------------------------------------------------

def detect_intent(text: str) -> dict | None:
    """
    Analisa texto e retorna a intenção de consulta, ou None se for registro.

    Args:
        text: Mensagem recebida pelo usuário.

    Returns:
        {"tipo": str, "extra_params": dict} ou None.
    """
    if not text or not text.strip():
        return None

    tl = _norm(text)
    extra: dict = {}

    # ------------------------------------------------------------------
    # 1. FILTRO COMBINADO  ex: "gastei com uber essa semana"
    # ------------------------------------------------------------------
    m = re.search(
        r'(?:gastei|gastos|quanto gastei|gasto)\s+(?:com|em|no|na)\s+(\w+)'
        r'.*?\b(semana|mes|m[eê]s)\b',
        tl,
    )
    if m:
        return {
            "tipo": "filtro_combinado",
            "extra_params": {
                "categoria": m.group(1),
                "periodo": m.group(2),
            },
        }

    # ------------------------------------------------------------------
    # 2. HISTÓRICO / EXTRATO  ex: "extrato", "últimas 10 transações"
    # ------------------------------------------------------------------
    # "ultimas" como palavra solta foi removida propositalmente —
    #   causava falso positivo em "comprei as últimas 3 camisas".
    #   Requer agora: "transações/lançamentos" após (com ou sem número).
    if re.search(
        r'\b(extrato|historico|ultimas?\s+(?:\d+\s+)?transacoes|ultimas?\s+(?:\d+\s+)?lancamentos|transacoes|lancamentos)\b',
        tl,
    ):
        n_match = re.search(r'(\d+)', tl)
        extra["n"] = int(n_match.group(1)) if n_match else 5
        return {"tipo": "historico", "extra_params": extra}

    # ------------------------------------------------------------------
    # 3. MÊS PASSADO  ex: "quanto gastei mês passado"
    # ------------------------------------------------------------------
    if re.search(r'\b(m[eê]s passado|m[eê]s anterior|[uú]ltimo m[eê]s)\b', tl):
        return {"tipo": "mes_passado", "extra_params": {}}

    # ------------------------------------------------------------------
    # 4. RECEITAS DA SEMANA
    # ------------------------------------------------------------------
    if (
        re.search(r'\b(semana|semanal)\b', tl)
        and re.search(r'\b(ganhei|recebi|receitas|entradas)\b', tl)
    ):
        return {"tipo": "receitas_semana", "extra_params": {}}

    # ------------------------------------------------------------------
    # 5. GASTOS DE HOJE
    # ------------------------------------------------------------------
    if re.search(r'\b(hoje|do dia)\b', tl) and re.search(
        r'\b(gastei|gastos|total|despesa|saidas|saida|quanto)\b', tl
    ):
        return {"tipo": "hoje", "extra_params": {}}

    # ------------------------------------------------------------------
    # 6. GASTOS DA SEMANA
    # ------------------------------------------------------------------
    if re.search(r'\b(semana|semanal)\b', tl) and re.search(
        r'\b(gastei|gastos|total|despesa|quanto)\b', tl
    ):
        return {"tipo": "semana", "extra_params": {}}

    # ------------------------------------------------------------------
    # 7. RECEITAS DO MÊS  (must precede despesas — "total" would match both)
    # ------------------------------------------------------------------
    if re.search(r'\b(m[eê]s|mensal)\b', tl) and re.search(
        r'\b(ganhei|recebi|receitas|entradas)\b', tl
    ):
        return {"tipo": "receitas", "extra_params": {}}

    # ------------------------------------------------------------------
    # 8. GASTOS DO MÊS
    # ------------------------------------------------------------------
    if re.search(r'\b(m[eê]s|mensal)\b', tl) and re.search(
        r'\b(gastei|gastos|total|fatura|quanto)\b', tl
    ):
        return {"tipo": "despesas", "extra_params": {}}

    # ------------------------------------------------------------------
    # 9. CATEGORIAS  ex: "onde gastei?", "por categoria"
    # ------------------------------------------------------------------
    if re.search(r'\b(categoria|categorias|onde gastei|por categoria)\b', tl):
        return {"tipo": "categorias", "extra_params": {}}

    # ------------------------------------------------------------------
    # 10. SALDO
    # ------------------------------------------------------------------
    if re.search(r'\b(saldo|quanto tenho|quanto sobrou|meu saldo)\b', tl):
        return {"tipo": "saldo", "extra_params": {}}

    # ------------------------------------------------------------------
    # 11. RECEITAS GERAIS
    # ------------------------------------------------------------------
    if re.search(r'\b(ganhei|recebi|receitas|entradas)\b', tl) and re.search(
        r'\b(total|quanto|m[eê]s|mes)\b', tl
    ):
        return {"tipo": "receitas", "extra_params": {}}

    # ------------------------------------------------------------------
    # 12. INSIGHTS / RESUMO GERAL
    # ------------------------------------------------------------------
    if re.search(
        r'\b(resumo|insights?|como estao|como est[aã]o|visao geral|visão geral|overview|me mostra|financas|finan[çc]as)\b',
        tl,
    ):
        return {"tipo": "insights", "extra_params": {}}

    # ------------------------------------------------------------------
    # 13. FALLBACK: "quanto gastei?" sem período → despesas do mês atual
    # ------------------------------------------------------------------
    if re.search(r'\b(quanto gastei|qual meu gasto|meus gastos|quanto foi)\b', tl):
        return {"tipo": "despesas", "extra_params": {}}

    return None
