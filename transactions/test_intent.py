"""
Testes unitários para transactions/intent_detector.py

Cobre:
- Todas as intenções de consulta reconhecidas
- Mensagens de registro (None)
- Variações de linguagem natural
- Extração de parâmetros extras (filtro_combinado, historico)
"""

from django.test import SimpleTestCase
from transactions.intent_detector import detect_intent


class IntentDetectorConsultaTests(SimpleTestCase):
    """Mensagens que devem ser classificadas como consulta."""

    # --- saldo ---
    def test_saldo_simples(self):
        self.assertEqual(detect_intent("meu saldo")["tipo"], "saldo")

    def test_saldo_quanto_tenho(self):
        self.assertEqual(detect_intent("quanto tenho?")["tipo"], "saldo")

    def test_saldo_quanto_sobrou(self):
        self.assertEqual(detect_intent("quanto sobrou?")["tipo"], "saldo")

    # --- despesas do mês ---
    def test_despesas_mes(self):
        self.assertEqual(detect_intent("quanto gastei esse mês?")["tipo"], "despesas")

    def test_despesas_mensal(self):
        self.assertEqual(detect_intent("total mensal")["tipo"], "despesas")

    def test_despesas_fallback_sem_periodo(self):
        self.assertEqual(detect_intent("quanto gastei?")["tipo"], "despesas")

    def test_despesas_meus_gastos(self):
        self.assertEqual(detect_intent("quais foram meus gastos?")["tipo"], "despesas")

    # --- mes passado ---
    def test_mes_passado(self):
        self.assertEqual(detect_intent("quanto gastei mês passado?")["tipo"], "mes_passado")

    def test_mes_anterior(self):
        self.assertEqual(detect_intent("gastos do mês anterior")["tipo"], "mes_passado")

    def test_ultimo_mes(self):
        self.assertEqual(detect_intent("último mês quanto foi?")["tipo"], "mes_passado")

    # --- semana ---
    def test_semana(self):
        self.assertEqual(detect_intent("quanto gastei essa semana?")["tipo"], "semana")

    def test_semanal(self):
        self.assertEqual(detect_intent("total semanal")["tipo"], "semana")

    # --- hoje ---
    def test_hoje(self):
        self.assertEqual(detect_intent("quanto gastei hoje?")["tipo"], "hoje")

    def test_gastos_do_dia(self):
        self.assertEqual(detect_intent("gastos do dia")["tipo"], "hoje")

    # --- receitas ---
    def test_receitas(self):
        self.assertEqual(detect_intent("total de receitas do mês")["tipo"], "receitas")

    def test_recebi_quanto(self):
        self.assertEqual(detect_intent("quanto recebi esse mês?")["tipo"], "receitas")

    def test_receitas_semana(self):
        self.assertEqual(detect_intent("quanto ganhei essa semana?")["tipo"], "receitas_semana")

    # --- categorias ---
    def test_categorias(self):
        self.assertEqual(detect_intent("onde gastei?")["tipo"], "categorias")

    def test_por_categoria(self):
        self.assertEqual(detect_intent("gastos por categoria")["tipo"], "categorias")

    # --- insights / resumo ---
    def test_resumo(self):
        self.assertEqual(detect_intent("resumo financeiro")["tipo"], "insights")

    def test_como_estao(self):
        self.assertEqual(detect_intent("como estão minhas finanças?")["tipo"], "insights")

    def test_me_mostra(self):
        self.assertEqual(detect_intent("me mostra o resumo do mês")["tipo"], "insights")

    def test_visao_geral(self):
        self.assertEqual(detect_intent("visão geral")["tipo"], "insights")

    # --- histórico ---
    def test_extrato(self):
        self.assertEqual(detect_intent("extrato")["tipo"], "historico")

    def test_historico(self):
        self.assertEqual(detect_intent("histórico de transações")["tipo"], "historico")

    def test_ultimas_transacoes(self):
        result = detect_intent("últimas transações")
        self.assertEqual(result["tipo"], "historico")

    def test_historico_n_padrao(self):
        result = detect_intent("extrato")
        self.assertEqual(result["extra_params"]["n"], 5)

    def test_historico_n_customizado(self):
        result = detect_intent("últimas 10 transações")
        self.assertEqual(result["extra_params"]["n"], 10)

    # --- filtro combinado ---
    def test_filtro_combinado_semana(self):
        result = detect_intent("gastei com uber essa semana")
        self.assertEqual(result["tipo"], "filtro_combinado")
        self.assertIn("uber", result["extra_params"]["categoria"])
        self.assertIn("semana", result["extra_params"]["periodo"])

    def test_filtro_combinado_mes(self):
        result = detect_intent("quanto gastei com alimentação neste mês?")
        self.assertEqual(result["tipo"], "filtro_combinado")
        self.assertIn("alimenta", result["extra_params"]["categoria"])


class IntentDetectorRegistroTests(SimpleTestCase):
    """Mensagens de registro de transação — devem retornar None."""

    def test_registro_despesa_simples(self):
        self.assertIsNone(detect_intent("gastei 50 no mercado"))

    def test_registro_receita(self):
        self.assertIsNone(detect_intent("recebi 1500 de salário"))

    def test_registro_com_valor_e_descricao(self):
        self.assertIsNone(detect_intent("paguei 120 na farmácia"))

    def test_registro_compra(self):
        self.assertIsNone(detect_intent("comprei roupa por 80 reais"))

    def test_registro_valor_puro(self):
        # Valor puro sem contexto não é consulta
        self.assertIsNone(detect_intent("150"))

    def test_mensagem_vazia(self):
        self.assertIsNone(detect_intent(""))

    def test_mensagem_none(self):
        self.assertIsNone(detect_intent(None))

    def test_ola(self):
        self.assertIsNone(detect_intent("oi tudo bem"))


class IntentDetectorFalsoPositivoTests(SimpleTestCase):
    """
    Testes de regressão para falsos positivos corrigidos no Sprint 5.
    Garante que mensagens de registro não sejam confundidas com consultas.
    """

    def test_ultimas_compras_nao_e_historico(self):
        """'comprei as últimas 3 camisas' não deve virar historico."""
        self.assertIsNone(detect_intent("comprei as últimas 3 camisas por 45 reais"))

    def test_ultimas_unidades_nao_e_historico(self):
        """'gastei nas últimas 2 semanas' — período, não extrato de transações."""
        # Aceita-se retornar None; o importante é não retornar historico.
        result = detect_intent("gastei nas últimas 2 semanas")
        if result is not None:
            self.assertNotEqual(result["tipo"], "historico")

    def test_extrato_e_historico(self):
        """'extrato' ainda deve funcionar normalmente."""
        self.assertEqual(detect_intent("me manda o extrato")["tipo"], "historico")

    def test_ultimas_transacoes_e_historico(self):
        """'últimas transações' deve retornar historico."""
        self.assertEqual(detect_intent("me mostra as últimas transações")["tipo"], "historico")

    def test_ultimas_5_e_historico(self):
        """'últimas 5 transações' deve retornar historico."""
        self.assertEqual(detect_intent("me manda as últimas 5 transações")["tipo"], "historico")
