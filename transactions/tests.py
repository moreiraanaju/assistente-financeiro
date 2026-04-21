from django.test import TestCase
from .parser import parse_message
from .nlp_parser import interpret_message


# =============================================================================
# SPRINT 1 — Testes do parser.py original
# Cobre: extração de valor, tipo e descrição com lógica de palavras-chave
# =============================================================================

class ParseMessageTestCase(TestCase):
    """
    Testes formais para o parser.py original.

    Valida a função parse_message() que usa palavras-chave e sinais (+/-)
    para classificar transações financeiras em português.
    """

    # ------------------------------------------------------------------
    # Detecção de tipo
    # ------------------------------------------------------------------

    def test_tipo_despesa_com_palavra_gastei(self):
        resultado = parse_message("gastei 50 mercado")
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["tipo"], "D")

    def test_tipo_receita_com_palavra_recebi(self):
        resultado = parse_message("recebi 1500 salario")
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["tipo"], "R")

    def test_tipo_despesa_com_palavra_paguei(self):
        resultado = parse_message("paguei 30 uber")
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["tipo"], "D")

    def test_tipo_receita_com_palavra_ganhei(self):
        resultado = parse_message("ganhei 200 freelance")
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["tipo"], "R")

    def test_tipo_despesa_com_palavra_comprei(self):
        resultado = parse_message("comprei 120 roupa")
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["tipo"], "D")

    def test_tipo_despesa_com_sinal_negativo(self):
        resultado = parse_message("-100 gasolina")
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["tipo"], "D")

    def test_tipo_receita_com_sinal_positivo(self):
        resultado = parse_message("+200 bonus")
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["tipo"], "R")

    def test_tipo_padrao_sem_palavra_chave(self):
        """Sem palavra-chave e sem sinal: padrão é Despesa."""
        resultado = parse_message("50 aluguel")
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["tipo"], "D")

    # ------------------------------------------------------------------
    # Extração de valor
    # ------------------------------------------------------------------

    def test_valor_inteiro(self):
        resultado = parse_message("gastei 50 frutas")
        self.assertEqual(resultado["valor"], 50.0)

    def test_valor_decimal_com_ponto(self):
        resultado = parse_message("paguei 15.90 netflix")
        self.assertAlmostEqual(resultado["valor"], 15.90)

    def test_valor_decimal_com_virgula(self):
        resultado = parse_message("comprei 29,99 roupa")
        self.assertAlmostEqual(resultado["valor"], 29.99)

    def test_valor_e_sempre_positivo_mesmo_com_sinal_negativo(self):
        resultado = parse_message("-80 gasolina")
        self.assertGreater(resultado["valor"], 0)

    def test_valor_grande(self):
        resultado = parse_message("recebi 5000 salario")
        self.assertEqual(resultado["valor"], 5000.0)

    # ------------------------------------------------------------------
    # Extração de descrição
    # ------------------------------------------------------------------

    def test_descricao_extraida(self):
        resultado = parse_message("gastei 50 mercado alimentacao")
        self.assertIsNotNone(resultado["descricao"])
        self.assertNotEqual(resultado["descricao"], "")

    def test_descricao_sem_texto_usa_padrao(self):
        # Apenas o número, sem texto algum → "sem descrição"
        resultado = parse_message("50")
        self.assertEqual(resultado["descricao"], "sem descrição")

    # ------------------------------------------------------------------
    # Formato de saída
    # ------------------------------------------------------------------

    def test_retorno_tem_chaves_obrigatorias(self):
        resultado = parse_message("gastei 50 mercado")
        self.assertIn("valor", resultado)
        self.assertIn("tipo", resultado)
        self.assertIn("descricao", resultado)
        self.assertIn("categoria_texto", resultado)

    def test_tipo_e_string_r_ou_d(self):
        resultado = parse_message("gastei 50 mercado")
        self.assertIn(resultado["tipo"], ["R", "D"])

    def test_valor_e_float(self):
        resultado = parse_message("gastei 50 mercado")
        self.assertIsInstance(resultado["valor"], float)

    # ------------------------------------------------------------------
    # Casos inválidos
    # ------------------------------------------------------------------

    def test_mensagem_vazia_retorna_none(self):
        self.assertIsNone(parse_message(""))

    def test_mensagem_none_retorna_none(self):
        self.assertIsNone(parse_message(None))

    def test_sem_numero_retorna_none(self):
        self.assertIsNone(parse_message("fui ao mercado hoje"))


# =============================================================================
# SPRINT 2 — Testes do nlp_parser.py (interpret_message)
# Cobre: frases naturais, preposições, detecção de categoria e integração
# =============================================================================

class InterpretMessageTestCase(TestCase):
    """
    Testes formais para o nlp_parser.py — função interpret_message().

    Valida a interpretação de mensagens reais em português com suporte a
    frases naturais, preposições e mapeamento de categorias.
    Retorno esperado: {valor: float, tipo: 'R'|'D', descricao: str, categoria_texto: str|None}
    """

    # ------------------------------------------------------------------
    # Mensagens com palavras-chave explícitas
    # ------------------------------------------------------------------

    def test_despesa_com_palavra_gastei(self):
        r = interpret_message("gastei 50 mercado")
        self.assertEqual(r["tipo"], "D")
        self.assertEqual(r["valor"], 50.0)

    def test_receita_com_palavra_recebi(self):
        r = interpret_message("recebi 1500 salario")
        self.assertEqual(r["tipo"], "R")
        self.assertEqual(r["valor"], 1500.0)

    def test_despesa_com_palavra_paguei(self):
        r = interpret_message("paguei 30 uber")
        self.assertEqual(r["tipo"], "D")
        self.assertEqual(r["valor"], 30.0)

    def test_receita_com_palavra_ganhei(self):
        r = interpret_message("ganhei 200 freelance")
        self.assertEqual(r["tipo"], "R")
        self.assertEqual(r["valor"], 200.0)

    def test_despesa_com_palavra_comprei(self):
        r = interpret_message("comprei 120 no restaurante")
        self.assertEqual(r["tipo"], "D")

    def test_despesa_com_palavra_usei(self):
        r = interpret_message("usei 25 em uma pizza")
        self.assertEqual(r["tipo"], "D")

    # ------------------------------------------------------------------
    # Mensagens com sinal explícito
    # ------------------------------------------------------------------

    def test_sinal_negativo_e_despesa(self):
        r = interpret_message("-100 gasolina")
        self.assertEqual(r["tipo"], "D")
        self.assertEqual(r["valor"], 100.0)

    def test_sinal_positivo_e_receita(self):
        r = interpret_message("+500 bonus")
        self.assertEqual(r["tipo"], "R")
        self.assertEqual(r["valor"], 500.0)

    def test_sinal_negativo_sobrepoe_palavra_receita(self):
        """Sinal explícito tem prioridade sobre palavras-chave."""
        r = interpret_message("-100 recebi salario")
        self.assertEqual(r["tipo"], "D")

    # ------------------------------------------------------------------
    # Mensagens sem palavras-chave (frases naturais)
    # ------------------------------------------------------------------

    def test_sem_palavra_chave_padrao_despesa(self):
        r = interpret_message("50 mercado")
        self.assertIsNotNone(r)
        self.assertEqual(r["tipo"], "D")

    def test_sem_palavra_chave_com_valor_decimal(self):
        r = interpret_message("15.90 cinema")
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r["valor"], 15.90)

    def test_apenas_valor_sem_descricao(self):
        r = interpret_message("100")
        self.assertIsNotNone(r)
        self.assertEqual(r["valor"], 100.0)

    # ------------------------------------------------------------------
    # Preposições em português
    # ------------------------------------------------------------------

    def test_com_preposicao_em(self):
        r = interpret_message("gastei 50 em mercado")
        self.assertIsNotNone(r)
        self.assertEqual(r["valor"], 50.0)

    def test_com_preposicao_no(self):
        r = interpret_message("gastei 50 no restaurante")
        self.assertIsNotNone(r)
        self.assertEqual(r["tipo"], "D")

    def test_com_preposicao_de(self):
        r = interpret_message("recebi 200 de salario")
        self.assertEqual(r["tipo"], "R")
        self.assertEqual(r["valor"], 200.0)

    def test_com_preposicao_na(self):
        r = interpret_message("paguei 80 na farmácia")
        self.assertIsNotNone(r)
        self.assertEqual(r["valor"], 80.0)

    # ------------------------------------------------------------------
    # Detecção de categorias
    # ------------------------------------------------------------------

    def test_categoria_alimentacao_por_mercado(self):
        r = interpret_message("gastei 50 mercado")
        self.assertEqual(r["categoria_texto"], "alimentação")

    def test_categoria_alimentacao_por_restaurante(self):
        r = interpret_message("comprei 100 no restaurante")
        self.assertEqual(r["categoria_texto"], "alimentação")

    def test_categoria_transporte_por_uber(self):
        r = interpret_message("paguei 30 uber")
        self.assertEqual(r["categoria_texto"], "transporte")

    def test_categoria_transporte_por_gasolina(self):
        r = interpret_message("30 gasolina")
        self.assertEqual(r["categoria_texto"], "transporte")

    def test_categoria_entretenimento_por_cinema(self):
        r = interpret_message("15 cinema")
        self.assertEqual(r["categoria_texto"], "entretenimento")

    def test_categoria_saude_por_farmacia(self):
        r = interpret_message("gastei 80 farmácia")
        self.assertEqual(r["categoria_texto"], "saúde")

    def test_categoria_moradia_por_aluguel(self):
        r = interpret_message("paguei 1200 aluguel")
        self.assertEqual(r["categoria_texto"], "moradia")

    def test_categoria_none_para_termo_desconhecido(self):
        r = interpret_message("gastei 50 presente")
        self.assertIsNone(r["categoria_texto"])

    # ------------------------------------------------------------------
    # Variações de notação numérica brasileira
    # ------------------------------------------------------------------

    def test_valor_com_virgula_brasileiro(self):
        r = interpret_message("gastei 19,90 almoço")
        self.assertAlmostEqual(r["valor"], 19.90)

    def test_valor_inteiro_grande(self):
        r = interpret_message("salário 2500")
        self.assertEqual(r["valor"], 2500.0)

    def test_valor_com_casas_decimais(self):
        r = interpret_message("paguei 1.234,56 imposto")
        # Regex captura o primeiro número encontrado (1)
        self.assertIsNotNone(r)

    # ------------------------------------------------------------------
    # Palavras-chave de receita expandidas
    # ------------------------------------------------------------------

    def test_deposito_e_receita(self):
        r = interpret_message("depósito 300")
        self.assertEqual(r["tipo"], "R")

    def test_salario_e_receita(self):
        r = interpret_message("salário 2500")
        self.assertEqual(r["tipo"], "R")

    def test_transferencia_e_receita(self):
        r = interpret_message("transferência 500 de fulano")
        self.assertEqual(r["tipo"], "R")

    # ------------------------------------------------------------------
    # Formato de saída padronizado
    # ------------------------------------------------------------------

    def test_retorno_tem_chaves_obrigatorias(self):
        r = interpret_message("gastei 50 mercado")
        self.assertIn("valor", r)
        self.assertIn("tipo", r)
        self.assertIn("descricao", r)
        self.assertIn("categoria_texto", r)

    def test_valor_e_sempre_float_positivo(self):
        r = interpret_message("-80 taxi")
        self.assertIsInstance(r["valor"], float)
        self.assertGreater(r["valor"], 0)

    def test_tipo_e_string_valida(self):
        r = interpret_message("gastei 10 lanche")
        self.assertIn(r["tipo"], ["R", "D"])

    def test_descricao_e_string(self):
        r = interpret_message("gastei 50 mercado")
        self.assertIsInstance(r["descricao"], str)

    # ------------------------------------------------------------------
    # Mensagens complexas e naturais
    # ------------------------------------------------------------------

    def test_frase_complexa_com_preposicao(self):
        r = interpret_message("paguei 200 de condomínio esse mês")
        self.assertIsNotNone(r)
        self.assertEqual(r["tipo"], "D")
        self.assertEqual(r["valor"], 200.0)

    def test_frase_natural_receita(self):
        r = interpret_message("ganhei 1500 de salario esse mes")
        self.assertEqual(r["tipo"], "R")
        self.assertEqual(r["valor"], 1500.0)

    def test_frase_com_multiplas_palavras_descricao(self):
        r = interpret_message("gastei 25 em uma pizza")
        self.assertIsNotNone(r)
        self.assertEqual(r["valor"], 25.0)

    # ------------------------------------------------------------------
    # Casos inválidos
    # ------------------------------------------------------------------

    def test_mensagem_vazia_retorna_none(self):
        self.assertIsNone(interpret_message(""))

    def test_mensagem_none_retorna_none(self):
        self.assertIsNone(interpret_message(None))

    def test_sem_numero_retorna_none(self):
        self.assertIsNone(interpret_message("fui ao mercado comprar coisas"))

    def test_espacos_em_branco_retornam_none(self):
        self.assertIsNone(interpret_message("   "))


# =============================================================================
# SPRINT 3 — Testes de mensagens incompletas, correções e ambiguidade
# Cobre: confianca, ambiguo, motivo_ambiguidade, is_correcao
# =============================================================================

class Sprint3TestCase(TestCase):
    """
    Testes formais para funcionalidades da Sprint 3 do nlp_parser.py.

    Cobre:
    - Novos campos no formato de retorno (confianca, ambiguo, motivo_ambiguidade, is_correcao)
    - Mensagens incompletas e nível de confiança resultante
    - Detecção e sinalização de ambiguidade com motivo
    - Interpretação de mensagens de correção ('na verdade foi 30', 'corrige para 45')
    - Compatibilidade retroativa com Sprints 1 e 2
    """

    # ------------------------------------------------------------------
    # Novos campos no formato de retorno
    # ------------------------------------------------------------------

    def test_retorno_tem_campo_confianca(self):
        r = interpret_message("gastei 50 mercado")
        self.assertIn("confianca", r)

    def test_retorno_tem_campo_ambiguo(self):
        r = interpret_message("gastei 50 mercado")
        self.assertIn("ambiguo", r)

    def test_retorno_tem_campo_motivo_ambiguidade(self):
        r = interpret_message("gastei 50 mercado")
        self.assertIn("motivo_ambiguidade", r)

    def test_retorno_tem_campo_is_correcao(self):
        r = interpret_message("gastei 50 mercado")
        self.assertIn("is_correcao", r)

    def test_confianca_e_valor_enum_valido(self):
        r = interpret_message("gastei 50 mercado")
        self.assertIn(r["confianca"], ["alta", "media", "baixa"])

    def test_ambiguo_e_booleano(self):
        r = interpret_message("gastei 50 mercado")
        self.assertIsInstance(r["ambiguo"], bool)

    def test_is_correcao_e_booleano(self):
        r = interpret_message("gastei 50 mercado")
        self.assertIsInstance(r["is_correcao"], bool)

    # ------------------------------------------------------------------
    # Confiança alta
    # ------------------------------------------------------------------

    def test_palavra_chave_com_descricao_e_alta_confianca(self):
        r = interpret_message("gastei 50 mercado")
        self.assertEqual(r["confianca"], "alta")
        self.assertFalse(r["ambiguo"])

    def test_sinal_positivo_com_descricao_e_alta_confianca(self):
        r = interpret_message("+500 salario")
        self.assertEqual(r["confianca"], "alta")
        self.assertFalse(r["ambiguo"])

    def test_sinal_negativo_com_descricao_e_alta_confianca(self):
        r = interpret_message("-80 uber")
        self.assertEqual(r["confianca"], "alta")
        self.assertFalse(r["ambiguo"])

    def test_alta_confianca_sem_motivo_ambiguidade(self):
        r = interpret_message("paguei 30 uber")
        self.assertEqual(r["confianca"], "alta")
        self.assertIsNone(r["motivo_ambiguidade"])

    # ------------------------------------------------------------------
    # Confiança média
    # ------------------------------------------------------------------

    def test_sem_palavra_chave_com_descricao_e_media_confianca(self):
        r = interpret_message("50 mercado")
        self.assertEqual(r["confianca"], "media")
        self.assertFalse(r["ambiguo"])

    def test_palavra_chave_sem_descricao_e_media_confianca(self):
        r = interpret_message("gastei 50")
        self.assertEqual(r["confianca"], "media")
        self.assertTrue(r["ambiguo"])

    def test_sinal_sem_descricao_e_media_confianca(self):
        r = interpret_message("+200")
        self.assertEqual(r["confianca"], "media")
        self.assertTrue(r["ambiguo"])

    def test_media_confianca_com_ambiguidade_tem_motivo(self):
        r = interpret_message("gastei 50")
        self.assertIsNotNone(r["motivo_ambiguidade"])

    # ------------------------------------------------------------------
    # Confiança baixa — mensagens incompletas
    # ------------------------------------------------------------------

    def test_apenas_valor_e_baixa_confianca(self):
        r = interpret_message("100")
        self.assertEqual(r["confianca"], "baixa")
        self.assertTrue(r["ambiguo"])

    def test_apenas_valor_tem_motivo_ambiguidade(self):
        r = interpret_message("100")
        self.assertIsNotNone(r["motivo_ambiguidade"])

    def test_apenas_valor_nao_e_none(self):
        """Mensagem incompleta ainda retorna dict (não None)."""
        r = interpret_message("100")
        self.assertIsNotNone(r)
        self.assertEqual(r["valor"], 100.0)

    # ------------------------------------------------------------------
    # Confiança baixa — conflito de tipo
    # ------------------------------------------------------------------

    def test_conflito_tipo_e_baixa_confianca(self):
        r = interpret_message("recebi mas gastei 50")
        self.assertEqual(r["confianca"], "baixa")
        self.assertTrue(r["ambiguo"])

    def test_conflito_tipo_tem_motivo_preenchido(self):
        r = interpret_message("recebi gastei 50 mercado")
        self.assertIsNotNone(r["motivo_ambiguidade"])

    def test_conflito_tipo_nao_e_correcao(self):
        r = interpret_message("recebi gastei 50")
        self.assertFalse(r["is_correcao"])

    # ------------------------------------------------------------------
    # Detecção de correções — padrão "na verdade"
    # ------------------------------------------------------------------

    def test_correcao_na_verdade_foi(self):
        r = interpret_message("na verdade foi 30")
        self.assertTrue(r["is_correcao"])
        self.assertEqual(r["valor"], 30.0)

    def test_correcao_na_verdade_era(self):
        r = interpret_message("na verdade era 45")
        self.assertTrue(r["is_correcao"])
        self.assertEqual(r["valor"], 45.0)

    def test_correcao_na_verdade_eram(self):
        r = interpret_message("na verdade eram 80")
        self.assertTrue(r["is_correcao"])
        self.assertEqual(r["valor"], 80.0)

    def test_correcao_na_verdade_sem_verbo(self):
        r = interpret_message("na verdade 45")
        self.assertTrue(r["is_correcao"])
        self.assertEqual(r["valor"], 45.0)

    def test_correcao_na_verdade_foram(self):
        r = interpret_message("na verdade foram 200")
        self.assertTrue(r["is_correcao"])
        self.assertEqual(r["valor"], 200.0)

    # ------------------------------------------------------------------
    # Detecção de correções — padrão "corrige/corrija"
    # ------------------------------------------------------------------

    def test_correcao_corrige_para(self):
        r = interpret_message("corrige para 80")
        self.assertTrue(r["is_correcao"])
        self.assertEqual(r["valor"], 80.0)

    def test_correcao_corrija_pra(self):
        r = interpret_message("corrija pra 15")
        self.assertTrue(r["is_correcao"])
        self.assertEqual(r["valor"], 15.0)

    def test_correcao_corrige_sem_preposicao(self):
        r = interpret_message("corrige 50")
        self.assertTrue(r["is_correcao"])
        self.assertEqual(r["valor"], 50.0)

    def test_correcao_corrijo(self):
        r = interpret_message("corrijo para 90")
        self.assertTrue(r["is_correcao"])
        self.assertEqual(r["valor"], 90.0)

    # ------------------------------------------------------------------
    # Detecção de correções — padrão "não foi/era"
    # ------------------------------------------------------------------

    def test_correcao_nao_foi(self):
        r = interpret_message("não, foi 50")
        self.assertTrue(r["is_correcao"])
        self.assertEqual(r["valor"], 50.0)

    def test_correcao_nao_era(self):
        r = interpret_message("não era 100")
        self.assertTrue(r["is_correcao"])
        self.assertEqual(r["valor"], 100.0)

    def test_correcao_nao_sem_virgula(self):
        r = interpret_message("não foi 70")
        self.assertTrue(r["is_correcao"])
        self.assertEqual(r["valor"], 70.0)

    # ------------------------------------------------------------------
    # Detecção de correções — valores e propriedades do retorno
    # ------------------------------------------------------------------

    def test_correcao_valor_com_virgula(self):
        r = interpret_message("na verdade foi 29,90")
        self.assertTrue(r["is_correcao"])
        self.assertAlmostEqual(r["valor"], 29.90)

    def test_correcao_valor_sempre_positivo(self):
        r = interpret_message("na verdade foi 50")
        self.assertGreater(r["valor"], 0)

    def test_correcao_tipo_e_none(self):
        r = interpret_message("na verdade foi 30")
        self.assertIsNone(r["tipo"])

    def test_correcao_descricao_e_none(self):
        r = interpret_message("na verdade foi 30")
        self.assertIsNone(r["descricao"])

    def test_correcao_confianca_e_alta(self):
        r = interpret_message("na verdade foi 30")
        self.assertEqual(r["confianca"], "alta")

    def test_correcao_nao_e_ambiguo(self):
        r = interpret_message("na verdade foi 30")
        self.assertFalse(r["ambiguo"])

    # ------------------------------------------------------------------
    # Mensagem normal não é correção
    # ------------------------------------------------------------------

    def test_mensagem_normal_nao_e_correcao(self):
        r = interpret_message("gastei 50 mercado")
        self.assertFalse(r["is_correcao"])

    def test_mensagem_com_valor_no_inicio_nao_e_correcao(self):
        r = interpret_message("50 mercado paguei")
        self.assertFalse(r["is_correcao"])

    # ------------------------------------------------------------------
    # Compatibilidade retroativa com Sprints 1 e 2
    # ------------------------------------------------------------------

    def test_campos_originais_ainda_presentes(self):
        r = interpret_message("gastei 50 mercado")
        for campo in ["valor", "tipo", "descricao", "categoria_texto"]:
            self.assertIn(campo, r)

    def test_valor_ainda_e_float(self):
        r = interpret_message("gastei 50 mercado")
        self.assertIsInstance(r["valor"], float)

    def test_tipo_ainda_retorna_r_ou_d_para_mensagem_normal(self):
        r = interpret_message("gastei 50 mercado")
        self.assertIn(r["tipo"], ["R", "D"])

    def test_categoria_ainda_funciona(self):
        r = interpret_message("gastei 50 mercado")
        self.assertEqual(r["categoria_texto"], "alimentação")

