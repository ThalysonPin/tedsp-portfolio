## Visão geral

**Landpages** é um projeto autoral de **Thalyson Emanuel (TEDSP)**, em produção, que apresenta sites e landing pages para negócios locais por meio de **quatro demos navegáveis**: estética, academia, odontologia e advocacia.

O projeto reúne apresentação dos estudos de interface, ferramentas interativas e jornadas que preparam mensagens de WhatsApp a partir das escolhas do visitante.

**Acessar o projeto:** [landpages.tedsptech.com](https://landpages.tedsptech.com/).

As demos são projetos-conceito: suas marcas, pessoas, endereços e números são fictícios.

## Contexto e problema

Um site para negócios locais precisa responder às dúvidas do público e apoiar o próximo passo do contato. O Landpages demonstra como identidade visual, conteúdo, interação e contexto da mensagem podem variar conforme o nicho e a intenção do visitante.

## Minha atuação

Projeto autoral com pesquisa de público, definição das jornadas, redação, identidade visual, desenvolvimento das páginas e interações, preparação dos materiais de demonstração e publicação.

## Imagens do projeto

### Portfólio público em produção

![Página pública do Landpages, com apresentação dos sites para negócios locais e prévia da demo de academia](imagens/01-site-em-producao.jpg)

Captura da aplicação publicada. Os exemplos apresentados pertencem às marcas fictícias das demos.

## Stack e arquitetura

| Camada | Tecnologia / recurso | Responsabilidade |
| --- | --- | --- |
| Estrutura | HTML semântico | Conteúdo, seções e organização das páginas |
| Apresentação | CSS responsivo | Identidade visual por nicho e adaptação a computador e celular |
| Interações | JavaScript | Seletores, simuladores, formulários e composição das mensagens |
| Demonstração | Iframes e imagens de prévia | Teste das demos no portfólio e abertura em tela cheia |
| Contato | Links de WhatsApp | Abertura de mensagens com o contexto selecionado pelo visitante |
| Descoberta | Metadados e dados estruturados JSON-LD | Representação do conteúdo e das informações dos negócios de demonstração |
| Publicação | Nginx, Docker e Coolify | Entrega das páginas estáticas no domínio público |

**Fluxo principal:** seleção do nicho → consulta e teste da demo → escolhas do visitante → mensagem preparada para abrir no WhatsApp.

## Demos e responsabilidades

### 1. Nuance Estética

**Objetivo:** apresentar uma jornada de avaliação voltada a quem pesquisa procedimentos estéticos.

**Principais funções:** mapa interativo de regiões do rosto, consulta das opções e preparação de um pedido de avaliação com região, dia e horário.

### 2. Usina Clube de Treino

**Objetivo:** demonstrar uma experiência para conhecer a academia e planejar o treino.

**Principais funções:** visualização ilustrativa de lotação, calculadora de anilhas e estimativa de carga, filtros de modalidades e planos e preparação de pedidos de aula experimental.

Os números de ocupação e demais dados da marca são demonstrativos.

### 3. Alvor Odontologia

**Objetivo:** apresentar informações e interações para quem pesquisa tratamentos odontológicos.

**Principais funções:** apresentação visual do planejamento do sorriso, escala ilustrativa de tonalidades e opções de contato que registram as preferências do visitante, incluindo uma abordagem mais gradual para quem tem receio do atendimento.

### 4. Ferraz Lobato Advogados

**Objetivo:** demonstrar a apresentação de um escritório e a organização de um primeiro contato.

**Principais funções:** simulador de prazos, indicação do próximo período de resposta e preparação da mensagem com as informações selecionadas na jornada.

Os simuladores fazem parte de uma demonstração de interface e não substituem avaliação profissional de um caso concreto.

## Recursos compartilhados

- Portfólio com seleção de nicho, carrossel de detalhes e visualização das páginas.
- Demos testáveis dentro da página e em tela cheia.
- Comparações entre mensagem genérica e mensagem preparada pelas interações.
- Temas claro e escuro com preferência salva.
- Navegação responsiva e textos organizados por público.
- Metadados, HTML semântico e dados estruturados nas páginas de demonstração.
- Contato comercial com escolha do tipo de negócio e montagem da mensagem de WhatsApp.

A montagem da mensagem não realiza o envio automaticamente: o visitante abre o WhatsApp e decide enviá-la. As demos também não representam reservas reais em agendas de clínicas ou empresas.

## Decisões técnicas

| Decisão | Motivo e efeito |
| --- | --- |
| Identidade própria para cada nicho | Demonstrar diferentes necessidades de conteúdo, confiança e interação |
| Demos utilizáveis em vez de apenas imagens | Permitir que o visitante percorra e avalie as jornadas |
| Mensagem de WhatsApp contextualizada | Levar as escolhas feitas na página para o início do contato |
| Páginas estáticas com JavaScript | Implementar as experiências de demonstração e servi-las sem um backend transacional |
| Identificação explícita dos projetos-conceito | Separar as demonstrações de trabalhos realizados para clientes reais |

## Entrega

- Portfólio autoral em produção com quatro demos de segmentos diferentes.
- Interações e roteiros de teste disponíveis ao visitante.
- Apresentação de decisões de UX, conteúdo e implementação.
- Canal de contato para desenvolvimento de sites para negócios locais.

O projeto não apresenta métricas próprias de conversão ou resultados comerciais das marcas fictícias.
