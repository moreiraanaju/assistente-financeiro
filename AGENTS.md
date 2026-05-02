# AGENTS.md
Guia técnico para desenvolvimento e evolução do **Assistente Financeiro via WhatsApp**.

Para contexto acadêmico completo (objetivos, justificativa, escopo e referências), ver [docs/detalhamento-evolucao.md](docs/detalhamento-evolucao.md).

---

## Stack Técnica

| Camada | Tecnologia |
|---|---|
| Backend | Django 4.x (Python) |
| Banco de dados | PostgreSQL 16 |
| Cache / Contexto | Redis 7 |
| Comunicação WhatsApp | Uazapi (Evolution API compatível) |
| Containerização | Docker + Docker Compose |
| NLP | Abordagem híbrida (RegEx + heurísticas + fallback LLM) |

---

## Estrutura de Pastas

```
assistente-financeiro/
├── core/               # Configurações Django (settings, urls, wsgi, asgi)
├── transactions/       # App principal
│   ├── models.py       # Transacao, Category
│   ├── nlp_parser.py   # Parser NLP (híbrido)
│   ├── parser.py       # Parser legado (RegEx)
│   ├── services.py     # Identificação de categoria
│   ├── serializers.py
│   ├── views.py        # Endpoints REST (consultas financeiras)
│   └── migrations/
├── users/              # Gestão de usuários Django
├── whatsapp/           # Integração Uazapi
│   ├── views.py        # Webhook principal (evolution_webhook)
│   ├── models.py       # Model Message
│   └── urls.py
├── docs/               # Documentação acadêmica e de evolução
├── docker-compose.yml  # Serviços: db, redis, web
├── Dockerfile
├── .env
└── manage.py
```

---

## Fluxo de uma Mensagem

```
WhatsApp → Uazapi → POST /whatsapp/webhook/
    └── evolution_webhook()
            ├── Segurança (apikey)
            ├── Detecção de intenção (consulta via RegEx)
            │       └── GET /api/consulta/?tipo=...
            │               └── resposta formatada → send_evolution_message()
            └── Cadastro de transação
                    ├── parse_message() — nlp_parser.py
                    ├── identificar_categoria()
                    ├── TransacaoSerializer.save()
                    └── send_evolution_message()
```

---

## Branch e Sprint Atual

**Branch:** `feature/webhook-nlp-integration`
**Sprint:** Sprint 3 — Contexto Conversacional com Redis

### Objetivo da Sprint 3
Implementar memória de curto prazo por usuário para que o assistente consiga:
- Complementar dados ausentes em mensagens incompletas (ex: "foi 80" após "gastei no mercado")
- Interpretar correções referenciando a transação anterior
- Responder perguntas de continuidade sem repetir contexto

### Implementação do Contexto
- **Chave Redis:** `contexto:{numero_whatsapp}` (ex: `contexto:5511999990000`)
- **TTL:** 600 segundos (10 minutos)
- **Estrutura do valor:** JSON com os campos da última interação parseada
  ```json
  {
    "ultimo_texto": "gastei no mercado",
    "ultimo_parsed": { "tipo": "D", "valor": null, "descricao": "mercado" },
    "timestamp": "2026-05-02T10:00:00"
  }
  ```

---

## Próximas Tarefas

### Sprint 3 — Em andamento
- [ ] Conectar Redis no Django via `django-redis` ou `redis-py`
- [ ] Criar helper `get_context(number)` / `set_context(number, data)` em `whatsapp/context.py`
- [ ] Integrar leitura/escrita de contexto em `evolution_webhook()` antes do parse
- [ ] Lógica de complementação: se `parsed_data` estiver incompleto, buscar contexto e tentar mesclar
- [ ] Testes manuais de fluxo conversacional (ex: mensagem em 2 partes)

### Sprint 4 — Insights Financeiros (próxima)
- [ ] Endpoint `/api/insights/` com resumo mensal, categoria líder e comparativo
- [ ] Detecção de intenção para comandos como "me mostra o resumo do mês"
- [ ] Geração de texto de insight para envio via WhatsApp

### Sprint 5 — Dashboard Web
- [ ] APIs DRF para alimentar gráficos
- [ ] Frontend com Chart.js (sem build toolchain)
- [ ] 4 cards de resumo + 2 gráficos + filtro de período

### Backlog Técnico
- [ ] Autenticação multi-usuário no webhook (hoje usa `User.objects.first()`)
- [ ] Testes automatizados no `whatsapp/views.py`
- [ ] Remover prints de debug restantes e padronizar logging

---

## Variáveis de Ambiente Relevantes

| Variável | Uso |
|---|---|
| `DATABASE_URL` | Conexão PostgreSQL |
| `REDIS_URL` | Conexão Redis (`redis://redis:6379/0`) |
| `UAZAPI_URL` | Base URL da instância Uazapi |
| `UAZAPI_TOKEN` | Token de autenticação Uazapi |
| `UAZAPI_INSTANCE_NAME` | Nome da instância WhatsApp |
| `EVOLUTION_BOT_KEY` | Chave de segurança do webhook |
| `API_BASE_URL` | URL interna do Django (para consultas self-call) |
