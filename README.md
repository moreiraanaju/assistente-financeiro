# Assistente Financeiro via WhatsApp

Sistema de controle financeiro pessoal integrado ao WhatsApp. Registre receitas e despesas enviando mensagens de texto — sem apps, sem planilhas.

---

## Tecnologias

| Tecnologia | Função |
|---|---|
| Python 3.12 + Django | Backend e regras de negócio |
| Django REST Framework | API RESTful |
| PostgreSQL | Persistência dos dados |
| WhatsApp Evolution API | Gateway de comunicação com o WhatsApp |
| Docker / Docker Compose | Ambiente isolado e reproduzível |

---

## Como rodar (primeira vez)

**Pré-requisitos:** [Docker Desktop](https://www.docker.com/products/docker-desktop) e [Git](https://git-scm.com/)

```bash
# 1. Clonar o repositório
git clone https://github.com/moreiraanaju/assistente-financeiro
cd assistente-financeiro

# 2. Criar o .env
cp .env.example .env          # Mac/Linux
copy .env.example .env        # Windows

# 3. Gerar SECRET_KEY e configurar o .env
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

No `.env`, configure:
```
SECRET_KEY=COLE_AQUI_A_CHAVE_GERADA
DEBUG=1
ALLOWED_HOSTS=*
DATABASE_URL=postgresql://app_user:app_password@db:5432/app_db
```

```bash
# 4. Subir os containers
docker compose up --build
```

Acesse: http://localhost:8000

```bash
# 5. Criar usuário admin (em outro terminal)
docker compose exec web python manage.py createsuperuser
```

Painel admin: http://localhost:8000/admin

---

## Arquitetura

O sistema segue o padrão **MVT do Django adaptado para API RESTful** — a camada de template é substituída por Serializers (JSON).

```
Webhook (WhatsApp)
        ↓
   urls.py          → roteamento da requisição HTTP
        ↓
   views.py         → orquestração das regras de negócio (APIView)
        ↓
   parser.py        → interpretação do texto via RegEx
        ↓
   serializers.py   → validação e conversão dos dados
        ↓
   models.py        → persistência via ORM no PostgreSQL
```

**Módulos da aplicação:**

```
assistente-financeiro/
├── core/            # configurações do projeto (settings, urls, wsgi)
├── transactions/    # lógica de transações: models, parser, views, serializers
├── users/           # gerenciamento de usuários
├── whatsapp/        # integração com a Evolution API
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Evolução planejada

O sistema está sendo evoluído no **Projeto Integrador (2026)** com as seguintes frentes:

- **NLP** — substituição do parser RegEx por interpretação em linguagem natural (abordagem híbrida com modelos externos para casos de baixa confiança)
- **Contexto conversacional** — o assistente passa a compreender sequências de mensagens, corrigir dados e manter contexto entre interações
- **Insights financeiros** — geração de resumos e análises sob demanda via WhatsApp (ex: "como estão meus gastos este mês?")
- **Dashboard analítico** — interface web com Chart.js mostrando saldo do mês, evolução de gastos por semana, distribuição por categoria e filtro de período

---

## Licença

Este projeto foi desenvolvido como trabalho acadêmico na UniSENAI Florianópolis.
