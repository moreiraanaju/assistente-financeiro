# Changelog — feature/nlp-parser

Registro das correções aplicadas à branch `feature/nlp-parser` antes do merge em `main`.
Relacionado à **Etapa 2 – Integração de interpretação em linguagem natural** (ver `docs/detalhamento-evolucao.md`).

---

## [fix] 2026-04-21 — Correções pré-merge (revisão de PR)

### Arquivos modificados
- `transactions/nlp_parser.py`
- `transactions/views.py`
- `whatsapp/views.py`
- `.gitignore`

---

### Fix 1 — Webhook de produção não tratava correções nem ambiguidade
**Arquivo:** `whatsapp/views.py`  
**Severidade:** 🔴 Crítico (bloqueador)

**Problema:**  
O PR adicionou a lógica de `is_correcao` e `ambiguo` apenas em `transactions/views.py`
(`WebhookTransactionView` — rota `/api/webhook/`), que é usada apenas em testes.
O webhook real de produção, `evolution_webhook()` em `whatsapp/views.py` (rota
`/whatsapp/webhook/`), recebia as mensagens dos usuários do WhatsApp mas não
tinha esses guards. Resultado:

- Mensagem de correção como `"na verdade foi 30"` → `parsed_data["tipo"]` retorna `None`
  → `tipo_banco = "OUT"` (porque `None != "R"`) → a correção era **silenciosamente
  ignorada e uma transação errada era salva**.
- Mensagem ambígua como `"50"` (só valor) → era salva sem pedir confirmação ao usuário,
  contrariando o objetivo de qualidade de dados do parser NLP.

**Correção:**  
Adicionados os blocos de guarda `is_correcao` e `ambiguo` dentro de `evolution_webhook()`,
imediatamente após a chamada a `parse_message()`, com o mesmo comportamento de
`WebhookTransactionView`:
- Correção → busca a última transação do usuário, deleta e recria com o novo valor,
  enviando confirmação pelo WhatsApp.
- Ambiguidade → envia mensagem de clarificação pelo WhatsApp sem salvar nada.

---

### Fix 2 — Deleção de transação sem tratamento de ProtectedError
**Arquivo:** `transactions/views.py` e `whatsapp/views.py`  
**Severidade:** 🟠 Alto (falha silenciosa em runtime)

**Problema:**  
A estratégia de correção adotada pelo PR é deletar a transação antiga e criar uma nova
(necessário porque `Transacao.value` é imutável por design). Porém, `Transacao.message`
usa `on_delete=PROTECT`: se a transação estiver vinculada a um registro de `Message`,
`ultima.delete()` lança `django.db.models.deletion.ProtectedError`, causando uma
exceção não tratada (HTTP 500) visível ao usuário como erro interno.

**Correção:**  
O bloco `ultima.delete() / nova.save()` foi envolvido em `try/except ProtectedError`
em ambos os arquivos (`WebhookTransactionView` e `evolution_webhook`). Em caso de erro,
o usuário recebe uma mensagem explicativa em vez de um 500.

> **Nota técnica para evolução futura:** a abordagem delete-and-recreate perde o
> histórico da transação original (id, created_at, FK para Message). Uma solução mais
> robusta seria adicionar campos `corrected_value` e `is_corrected` ao modelo
> `Transacao`, preservando o registro original. Isso está fora do escopo desta correção
> e deve ser avaliado na Etapa 3 (contexto conversacional).

---

### Fix 3 — Dois dicionários de categorias incompatíveis com o banco de dados
**Arquivo:** `transactions/nlp_parser.py`  
**Severidade:** 🔴 Crítico (bloqueador)

**Problema:**  
O PR introduziu `CATEGORIAS` em `nlp_parser.py` com chaves em letras minúsculas e
nomes diferentes dos registrados no banco de dados e em `services.MAPEAMENTO`:

| `nlp_parser.py` (PR original) | `services.py` (MAPEAMENTO / DB) |
|---|---|
| `"alimentação"` | `"Alimentação"` |
| `"transporte"` | `"Transporte"` |
| `"moradia"` | `"Casa"` |
| `"entretenimento"` | `"Lazer"` |
| *(ausente)* | `"Renda"`, `"Compras"`, `"Educação"`, `"Investimento"` |

O valor de `categoria_texto` é passado diretamente para:
```python
Category.objects.filter(name__iexact=parsed_data["categoria_texto"])
```
Com os nomes errados, a consulta não encontrava a categoria → fallback para `"Outros"`
em 100% dos casos onde o parser tinha detectado corretamente a categoria.

**Correção:**  
`CATEGORIAS` foi reescrito com:
- **Chaves idênticas às categorias do banco** (`"Alimentação"`, `"Transporte"`, `"Casa"`,
  `"Lazer"`, `"Renda"`, `"Compras"`, `"Educação"`, `"Investimento"`).
- **Palavras-chave expandidas** para cobrir variações com e sem acento (ex: `"farmacia"`
  e `"farmácia"`) e termos presentes em `services.MAPEAMENTO` que faltavam
  (ex: `"ifood"`, `"99"`, `"posto"`, `"poupança"`).
- **Detecção normalizada:** a função `_detecta_categoria()` agora usa `_normaliza()`
  (baseada em `unidecode`) para comparar texto e palavras-chave sem sensibilidade a
  acentos, garantindo que `"farmácia"` bata com `"farmacia"` no texto normalizado.

> **Manutenção:** `CATEGORIAS` (nlp_parser) e `MAPEAMENTO` (services) continuam sendo
> dicionários separados por razões de responsabilidade (parser vs. resolução de DB).
> Ao adicionar ou renomear categorias no banco, ambos devem ser atualizados.
> Uma refatoração futura pode unificá-los em um único módulo `categories.py`.

---

### Fix 4 — `_VERBOS_ACAO` recriado a cada chamada de função
**Arquivo:** `transactions/nlp_parser.py`  
**Severidade:** 🟡 Baixo (performance)

**Problema:**  
O conjunto `_VERBOS_ACAO` estava declarado dentro do corpo de `interpret_message()`,
sendo recriado em memória a cada chamada da função. Em um sistema de webhook que
processa cada mensagem recebida, isso é desnecessário.

**Correção:**  
`_VERBOS_ACAO` foi promovido a constante de módulo, declarada uma única vez no
nível do arquivo, junto às outras constantes (`PALAVRAS_RECEITA`, `PALAVRAS_DESPESA`).

---

### Fix 5 — Import duplicado em `transactions/views.py`
**Arquivo:** `transactions/views.py`  
**Severidade:** 🟡 Baixo (qualidade de código)

**Problema:**  
O arquivo tinha `from .services import identificar_categoria` em duas linhas separadas
(pré-existente no `main`, não introduzido pelo PR). Com a adição de `ProtectedError`,
os imports foram reorganizados.

**Correção:**  
Removida a linha duplicada. Os imports agora são:
```python
from django.db.models.deletion import ProtectedError
from .services import identificar_categoria, resolver_nome_categoria
```

---

### Fix 6 — `.vscode/` sem entrada no `.gitignore`
**Arquivo:** `.gitignore`  
**Severidade:** 🟡 Baixo (higiene de repositório)

**Problema:**  
O arquivo `.vscode/settings.json` foi commitado no PR, poluindo o histórico com
configurações locais de IDE que variam por desenvolvedor.

**Correção:**  
Adicionada a entrada `.vscode/` ao `.gitignore`. A entrada duplicada `*.pyc` também
foi removida.

---

## Resumo das correções

| # | Severidade | Arquivo | Descrição |
|---|---|---|---|
| 1 | 🔴 Crítico | `whatsapp/views.py` | Guards `is_correcao` e `ambiguo` no webhook de produção |
| 2 | 🟠 Alto | `transactions/views.py`, `whatsapp/views.py` | `try/except ProtectedError` na deleção de correção |
| 3 | 🔴 Crítico | `transactions/nlp_parser.py` | Sincronização de `CATEGORIAS` com nomes do banco |
| 4 | 🟡 Baixo | `transactions/nlp_parser.py` | `_VERBOS_ACAO` promovido a constante de módulo |
| 5 | 🟡 Baixo | `transactions/views.py` | Remoção de import duplicado |
| 6 | 🟡 Baixo | `.gitignore` | Adicionado `.vscode/`, removido `*.pyc` duplicado |
