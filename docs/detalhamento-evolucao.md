# DETALHAMENTO DO PROJETO
Evolução de Assistente Financeiro Conversacional via WhatsApp
com Processamento de Linguagem Natural e Dashboard Analítico

## CONTEXTO:
O projeto consiste na evolução de um sistema denominado Assistente Financeiro via
WhatsApp, desenvolvido anteriormente no Projeto Aplicado III. A solução permite que
usuários registrem receitas e despesas enviando mensagens diretamente pelo WhatsApp
utilizando linguagem natural como forma de interação.
Atualmente, o sistema interpreta as mensagens enviadas pelos usuários, identifica valores
monetários, categoriza transações e armazena essas informações em um banco de dados
para posterior consulta e análise. A arquitetura da aplicação utiliza Django (Python) no
backend, PostgreSQL para armazenamento de dados, Docker para gerenciamento do
ambiente e integração com a Evolution API para comunicação com o WhatsApp.
Entretanto, a solução atual apresenta limitações na interpretação das mensagens dos
usuários, pois o mecanismo de análise textual é baseado em expressões regulares (RegEx).
Essa abordagem funciona adequadamente em cenários simples, mas apresenta dificuldades
para lidar com variações linguísticas, diferentes formas de escrita e estruturas de frases
mais complexas.
Diante dessas limitações, este projeto propõe a evolução do sistema por meio da integração
de técnicas de processamento de linguagem natural, permitindo uma interpretação mais
flexível das mensagens enviadas pelos usuários. Além disso, serão incorporados
mecanismos de contexto conversacional e visualização analítica dos dados financeiros por
meio de um dashboard web, ampliando as funcionalidades do assistente financeiro e
melhorando a experiência de uso.

## OBJETIVOS:
### GERAL:
Evoluir o sistema de assistente financeiro integrado ao WhatsApp utilizando técnicas de
processamento de linguagem natural, análise de dados e visualização interativa, ampliando
a capacidade de interpretação das mensagens e geração de insights financeiros para apoio
ao controle financeiro dos usuários.

### ESPECÍFICOS:
• Substituir o parser baseado em RegEx por um mecanismo de interpretação em linguagem
natural para extração de informações financeiras das mensagens.
• Implementar contexto conversacional para continuidade da interação e complementação
de dados.
• Desenvolver geração de insights financeiros sob demanda a partir do histórico de
transações.
• Criar dashboard web para visualização analítica das informações financeiras registradas.
• Validar a solução com 3 a 5 usuários para avaliar a usabilidade e utilidade do sistema.

## JUSTIFICATIVA:
O controle financeiro pessoal ainda representa um desafio para muitas pessoas. Diversas
ferramentas disponíveis exigem o uso frequente de aplicativos específicos ou interfaces
complexas, o que pode dificultar o registro constante de receitas e despesas no dia a dia.
Neste contexto, utilizar o WhatsApp como interface de interação torna o acesso à ferramenta
mais simples e natural, considerando que o aplicativo é amplamente utilizado no Brasil. A
evolução do sistema permitirá melhorar a interpretação das mensagens enviadas pelos
usuários por meio de técnicas de processamento de linguagem natural, além de oferecer
análises e insights financeiros que auxiliem no acompanhamento das finanças pessoais.


## PLANO ESTRUTURAL (escopo):
1. Análise da solução existente
2. Integração de mecanismo de interpretação em linguagem natural.
3. Implementação de contexto conversacional
4. Desenvolvimento de insights financeiros
5. Criação de dashboard analítico
6. Validação com usuários
7. Testes e documentação


### Etapa 1 – Análise da solução existente
Nesta etapa será realizada a análise da arquitetura atual do sistema Assistente Financeiro
via WhatsApp desenvolvido no projeto anterior. O objetivo é compreender o funcionamento
da aplicação, identificar os componentes principais e avaliar as limitações do mecanismo
atual de interpretação de mensagens baseado em expressões regulares (RegEx).
Também serão analisados os fluxos de comunicação entre usuário, backend e banco de
dados, bem como as tecnologias utilizadas na implementação do sistema.

### Etapa 2 – Integração de interpretação em linguagem natural
Nesta etapa será implementado um mecanismo de interpretação em linguagem natural para
substituir o parser baseado em expressões regulares (RegEx). O objetivo é permitir que o
sistema identifique automaticamente informações presentes nas mensagens dos usuários,
como valores monetários, tipo de transação, categoria de gasto e descrição da transação.
A solução utilizará uma abordagem híbrida de processamento de linguagem natural,
priorizando a extração estruturada das informações a partir das mensagens e recorrendo a
modelos de linguagem externos em casos de baixa confiança ou ambiguidade na
interpretação.
Também será realizada uma fase de validação com mensagens em português brasileiro
para avaliar a precisão da interpretação e definir critérios mínimos de confiança para
extração das informações.

### Etapa 3 – Implementação de contexto conversacional
Nesta etapa será implementado um mecanismo de contexto conversacional que permita ao
sistema compreender sequências curtas de mensagens enviadas pelo usuário.
Esse contexto será utilizado para complementar informações ausentes, interpretar correções
feitas pelo usuário e responder comandos que dependem de mensagens anteriores. Dessa
forma, a interação com o assistente financeiro se torna mais natural e eficiente.

### Etapa 4 – Desenvolvimento de insights financeiros
Nesta etapa será desenvolvido um módulo responsável por gerar insights financeiros a
partir das transações registradas pelos usuários. Os insights serão gerados sob demanda,
ou seja, quando solicitados diretamente pelo usuário por meio da interface conversacional
no WhatsApp (por exemplo: “me mostra meu resumo da semana” ou “como estão meus
gastos este mês”).
O sistema analisará o histórico de receitas e despesas para apresentar indicadores simples,
como resumo financeiro do período, categorias com maior gasto e relação entre receitas e
despesas.
Essa abordagem permite oferecer análises úteis ao usuário mantendo uma arquitetura mais
simples e adequada ao escopo do projeto.

### Etapa 5 – Criação de dashboard analítico
Nesta etapa será desenvolvido um dashboard web interativo original para visualização
das informações financeiras registradas no sistema. A decisão por desenvolvimento próprio,
em vez de ferramentas prontas como Power BI ou Metabase, se justifica pela necessidade
de multi-tenancy nativo: cada usuário do WhatsApp deve visualizar exclusivamente seus
próprios dados, requisito que a autenticação já existente no Django resolve de forma direta e
segura.
O stack utilizado será Django REST Framework para exposição das APIs de dados e
Chart.js no frontend para renderização dos gráficos, sem necessidade de build toolchain
adicional. O escopo mínimo viável prevê: quatro cards de resumo (saldo do mês, maior
gasto, categoria líder e comparativo com o mês anterior); dois gráficos (evolução de gastos
por semana e distribuição por categoria); filtro de período; e botão de envio do resumo
financeiro diretamente pelo WhatsApp, integrando o dashboard à interface conversacional já
existente.

### Etapa 6 – Validação com usuários
Nesta etapa será realizada a validação do sistema com um pequeno grupo de usuários
(entre 3 e 5 participantes).
Os usuários irão testar as funcionalidades do assistente financeiro e fornecer feedback
sobre a experiência de uso por meio de formulários estruturados, permitindo avaliar a
usabilidade do sistema e identificar possíveis melhorias.

### Etapa 7 – Testes e documentação
Nesta etapa final serão realizados testes funcionais para verificar o correto funcionamento
das funcionalidades implementadas.
Também será realizada a organização do repositório do projeto, elaboração da
documentação técnica e preparação do material necessário para apresentação do projeto.


### RESULTADOS:
Espera-se que a solução evoluída apresente melhorias significativas na interpretação de
linguagem natural em comparação ao mecanismo anterior baseado em expressões
regulares.
Além disso, o sistema deverá permitir uma interação mais natural entre usuários e assistente
financeiro, oferecendo consultas, resumos e análises financeiras por meio de mensagens no
WhatsApp e visualização analítica através do dashboard web.


### REFERÊNCIAS:
Django Software Foundation. Django Documentation. Disponível em:
https://docs.djangoproject.com/
PostgreSQL Global Development Group. PostgreSQL Documentation. Disponível em:
https://www.postgresql.org/docs/
Evolution API. Evolution API Documentation. Disponível em: https://docs.evoapicloud.com
Urchade. GLiNER – Generalist Named Entity Recognizer. Disponível em:
https://github.com/urchade/GLiNER
Hugging Face. Natural Language Processing Documentation. Disponível em:
https://huggingface.co/docs
Google. Gemini API Documentation. Disponível em: https://ai.google.dev/docs
Chart.js. Chart.js Documentation. Disponível em: https://www.chartjs.org/docs/
