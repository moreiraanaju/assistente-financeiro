---
trigger: always_on
---

## Projeto: Assistente Financeiro — Dashboard

### Stack
- Python 3.12, Django 5.x, DRF 3.15, PostgreSQL
- Frontend: HTML + CSS puro + Chart.js via CDN (sem build toolchain, sem React, sem Vue)
- Docker para ambiente

### Restrições críticas
- NUNCA modifique transactions/models.py — o campo value é imutável por design
- NUNCA modifique whatsapp/views.py nem whatsapp/models.py
- NUNCA altere o endpoint GET /api/consulta/ — ele está em uso pelo WhatsApp
- NUNCA use settings.AUTH_USER_MODEL como users.User — o FK de Transacao aponta para auth.User
- NUNCA instale dependências sem listar e aguardar aprovação

### Comportamento esperado
- Antes de criar ou modificar qualquer arquivo, liste o que será alterado
- Aguarde confirmação antes de executar
- Trabalhe apenas dentro do app dashboard/ salvo instrução explícita em contrário
- Filtre sempre os dados por request.user — nunca exponha dados de outros usuários