# Diagramas Arquiteturais - Assistente Financeiro

Abaixo estão os diagramas representando a arquitetura, estrutura de dados, implantação e fluxos do Assistente Financeiro, baseados no escopo de evolução (incluindo NLP, Dashboard e integrações).

## 1. Diagrama Entidade-Relacionamento (ERD)
Modela as tabelas do banco de dados e suas cardinalidades. Repare que a tabela `Transacao` aponta para `auth_User` (padrão do Django), e o sistema também possui uma tabela `User` específica do app `users` independente para outros fins.

```mermaid
erDiagram
    auth_User ||--o{ Transacao : creates
    users_User {
        UUID id PK
        string name
        string phone_number
        datetime created_at
        datetime updated_at
        string time_zone
        string locale
    }
    Category ||--o{ Transacao : categorizes
    Category {
        int id PK
        string name
    }
    whatsapp_Message ||--o| Transacao : generates
    whatsapp_Message {
        int id PK
        string external_id
        datetime created_at
    }
    Transacao {
        int id PK
        int user_id FK
        int category_id FK
        int message_id FK
        string description
        datetime date_transaction
        decimal value
        string type
        datetime created_at
    }
```

## 2. Diagrama de Classes (UML)
Representação dos Models da aplicação, seus atributos principais e a associação entre as classes lógicas do sistema Django.

```mermaid
classDiagram
    class User {
        +UUID id
        +CharField name
        +CharField phone_number
        +DateTimeField created_at
        +DateTimeField updated_at
        +CharField time_zone
        +CharField locale
    }
    class Category {
        +int id
        +CharField name
        +__str__()
    }
    class Message {
        +int id
        +CharField external_id
        +DateTimeField created_at
        +__str__()
    }
    class Transacao {
        +int id
        +ForeignKey user
        +ForeignKey category
        +ForeignKey message
        +CharField description
        +DateTimeField date_transaction
        +DecimalField value
        +CharField type
        +DateTimeField created_at
        +save()
        +__str__()
    }
    Transacao --> "auth.User"
    Transacao --> Category
    Transacao --> Message
```

## 3. Diagrama de Componentes
Demonstra os grandes blocos lógicos da aplicação e como eles se comunicam para processar as transações, rodar a inteligência de NLP e servir o Dashboard.

```mermaid
graph TD
    subgraph Assistente Financeiro [Sistema Interno Django]
        WA[Módulo WhatsApp / Webhooks]
        Dash[Módulo Dashboard / API REST]
        NLP[Módulo NLP / Parser]
        TM[Módulo Gestor de Transações]
        RG[Módulo Gerador de Insights]
    end
    
    DB[(PostgreSQL)]
    Evo((Evolution API))
    LLM((Serviço LLM/GLiNER externo))

    Evo <-->|Webhooks POST / Envio| WA
    WA -->|Mensagem bruta| NLP
    NLP <-->|Requisição de Extração| LLM
    NLP -->|Dados Estruturados| TM
    TM <-->|Leitura/Escrita via ORM| DB
    Dash <-->|Consulta endpoints (API)| TM
    Dash -->|Geração Relatório| RG
    RG <-->|Consulta Histórico (Aggregate)| DB
```

## 4. Diagrama de Sequência (UML Comportamental)
Mapeia o fluxo assíncrono de quando o usuário envia uma mensagem de gasto até a resposta de confirmação do bot, ilustrando a cadeia de responsabilidade.

```mermaid
sequenceDiagram
    actor U as Usuário
    participant W as WhatsApp
    participant E as Evolution API
    participant D as Django (Webhook View)
    participant N as NLP Engine
    participant DB as Banco de Dados

    U->>W: "Gastei 50 no mercado hoje"
    W->>E: Redireciona Mensagem
    E->>D: POST /webhook (JSON payload)
    D->>N: Envia texto para interpretação
    N->>N: Extrai entidades: valor=50, cat="mercado", tipo=OUT
    D->>DB: Salva Transacao associada ao usuário
    D->>E: Retorna payload de confirmação (200 OK)
    E->>W: Entrega mensagem de volta
    W->>U: "Transação de R$ 50,00 salva com sucesso!"
```

## 5. Diagrama de Implantação
Representação física de como o sistema e a infraestrutura estão distribuídos. No caso deste projeto, baseado num ambiente Docker.

```mermaid
graph TD
    node_user[Dispositivos Cliente]
    
    subgraph Servidor Host
        subgraph Ambiente Docker Compose
            container_web[Container Django Web<br/>Porta 8000]
            container_db[Container PostgreSQL<br/>Porta 5432]
        end
    end
    
    cloud_evo[Evolution API Cloud]
    cloud_llm[Provedores de IA Externa]

    node_user -->|App WhatsApp| cloud_evo
    node_user -->|Navegador HTTPS| container_web
    
    cloud_evo <-->|Comunicação Webhooks HTTP| container_web
    container_web <-->|Rede Interna Docker TCP| container_db
    container_web <-->|API REST HTTPS| cloud_llm
```
