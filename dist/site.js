/* tedsptech: page-local behaviour. The engine (scrollcraft.js) is untouched;
   everything bespoke lives here and reads the engine's --sc-p off each act.

   Signature move: the visitor's message is the payload. It is parsed, used to
   rank real projects, carried through the system map, and composed into an
   email draft at the end. All of it runs locally; nothing is sent. */
(function () {
  'use strict';

  var sc = window.ScrollCraft ? window.ScrollCraft.mount(document.body) : null;
  var reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var finePointer = matchMedia('(hover: hover) and (pointer: fine)').matches;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var clamp01 = function (v) { return v < 0 ? 0 : v > 1 ? 1 : v; };

  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

  /* ------------------------------------------------------------ copy ---- */
  var PT = {
    'skip': 'Pular para o conteúdo',
    'navLabel': 'Pipeline', 'homeLabel': 'Thalyson Emanuel, início', 'langLabel': 'Idioma',
    'n.trigger': 'Gatilho', 'n.classify': 'Classificar', 'n.retrieve': 'Buscar', 'n.system': 'Sistema',
    'n.runs': 'Execuções', 'n.experience': 'Experiência', 'n.output': 'Saída',
    'cta': 'Baixar currículo', 'demoRun': 'Execução demo', 'chars': 'caracteres',
    'portraitAlt': 'Retrato de Thalyson Emanuel',
    'role': 'Desenvolvedor de IA e Automação',
    'intro': 'Desenvolvo agentes de IA e automações, e conecto os sistemas que times usam em atendimento, marketing e vendas.',
    'metaWhere': 'Brasil · Remoto', 'metaEnglish': 'Inglês C1', 'watch': 'Ver apresentação',
    'trig.kind': 'Gatilho · mensagem recebida', 'trig.waiting': 'aguardando',
    'trig.label': 'Para qual vaga você está contratando?', 'trig.hint': 'exemplo · edite · fica no seu navegador',
    'presetsLabel': 'Mensagens de exemplo',
    'p.full': 'Tempo integral', 'p.contract': 'Contrato', 'p.project': 'Projeto de clínica',
    'trig.note': 'Roda no seu navegador. Nada é enviado.', 'trig.run': 'Executar',
    'cl.kind': 'Classificar · leitor de intenção',
    'cl.title': 'Sua mensagem, lida do jeito que meus agentes leem o WhatsApp de uma clínica.',
    'cl.lede': 'Antes de responder um lead, o agente extrai do texto o que importa: o que a pessoa quer, como quer trabalhar e o que isso envolve. Aqui está uma versão simplificada, baseada em regras, desse passo, aplicada ao que você escreveu.',
    'cl.node': 'Campos extraídos', 'cl.state': 'por regras · local',
    'f.intent': 'Intenção', 'f.engagement': 'Formato', 'f.location': 'Local', 'f.focus': 'Envolve', 'f.language': 'Idioma',
    'noscript': 'O leitor precisa de JavaScript. O resto da página funciona sem ele.',
    'rt.kind': 'Buscar · base de conhecimento', 'rt.title': 'O que meu trabalho diz sobre isso.',
    'rt.lede': 'Fatos da minha experiência e, depois, meus projetos ranqueados pelos temas da sua mensagem.',
    'rt.node': 'Resultados da busca', 'rt.facts': 'Fatos · do meu currículo',
    'rt.f1': 'workflows desenvolvidos e mantidos', 'rt.f2': 'clínicas com agentes de pré-vendas com IA em que trabalhei', 'rt.f2s': 'B2Med · LLMs, CRMs, agendas',
    'rt.f3': 'clientes atendidos na consultoria Foltz', 'rt.matches': 'Melhores resultados · por palavras-chave',
    'sy.kind': 'Sistema · arquitetura que construí',
    'sy.title': 'Atendimento com IA para clínicas médicas, 10 módulos.',
    'sy.lede': 'Um workflow de entrada e nove subworkflows no n8n, com agentes, RAG, MCP e integrações com WhatsApp, CRMs e agendas de clínicas. Sua mensagem é o token.',
    'm1': 'Canal de entrada', 'm2': 'Kommo e ID de sessão', 'm3': 'Classificação e fila de mensagens',
    'm4': 'Agente de atendimento BASIC', 'm5': 'Agente MCP duplo', 'm6': 'Envio da resposta do agente',
    'm7': 'Aviso ao supervisor', 'm8': 'Atualização do RAG', 'm9': 'Reset', 'm10': 'Registro do histórico de conversas humanas',
    'servicesLabel': 'Serviços conectados', 'sy.log': 'Log de execução', 'logLabel': 'Log de execução',
    'sy.foot': 'Desenhado a partir da arquitetura de um sistema que construí no n8n para clínicas médicas. A execução é simulada no seu navegador.',
    'ru.kind': 'Execuções · histórico', 'ru.title': 'Sistemas que construí, em uso ou entregues.',
    'ru.lede': 'Os que combinam com a sua mensagem aparecem marcados.',
    'ru.si.f1': 'Dados do lead', 'ru.si.f2': 'Pesquisa digital', 'ru.si.f3': 'Análise com IA', 'ru.si.f4': 'Relatório comercial',
    'ru.inuse': 'Em uso · estudo de caso', 'ru.built': 'Entregue · estudo de caso', 'match': 'combina',
    'ru.si.t': 'Relatórios de inteligência comercial',
    'ru.si.d': 'Dados do lead, presença digital e concorrentes locais reunidos em um relatório que o closer usa na reunião. As análises das calls mostraram que os leads entenderam melhor a proposta.',
    'ru.ca.n': 'clínicas com agentes de pré-vendas com IA', 'ru.ca.t': 'Agentes de IA para clínicas',
    'ru.ca.d': 'Agentes que atendem e qualificam leads, conectados ao CRM da clínica e, em parte das operações, à agenda e ao prontuário.',
    'ru.wa.n': 'conversas analisadas em mais de 30 clínicas', 'ru.wa.big': '100.000+', 'ru.cl.s': 'n8n · IA', 'ex.1.s': 'IA · Automação · Docker · PostgreSQL · AWS', 'ru.wa.m': '2026 · único desenvolvedor',
    'ru.wa.t': 'Inteligência de conversas de WhatsApp',
    'ru.wa.d': 'Um CRM Kanban automático montado a partir das conversas das clínicas, com relatórios diários e um resumo semanal enviado no WhatsApp.',
    'ru.cl.f1': 'Call comercial', 'ru.cl.f2': 'Análise', 'ru.cl.f3': 'Informações estruturadas',
    'ru.cl.t': 'Análise de calls comerciais',
    'ru.cl.d': 'Transforma calls de vendas em notas estruturadas sobre como a proposta foi apresentada e o que o lead entendeu, para o time revisar e melhorar.',
    'ru.eb.alt': 'Página inicial do EverBetter: um campo de URL e o título “Seja encontrado. Seja a referência.”',
    'ru.live': 'No ar', 'open': 'Abrir site',
    'ru.eb.d': 'Um app que analisa um site para SEO e buscas com IA e devolve recomendações claras. A análise é gratuita.',
    'ru.lp.alt': 'Página inicial do Landpages com abas de demos de estética, academia, odontologia e advocacia',
    'ru.lp.d': 'Sites para negócios locais, com quatro demos funcionando (estética, academia, odontologia, advocacia) que montam uma mensagem de WhatsApp a partir das escolhas do visitante.',
    'ru.px.n': 'inscrições vendidas no torneio', 'ru.px.m': '2024 · único desenvolvedor',
    'ru.px.t': 'Checkout Pix para torneio de beach tennis',
    'ru.px.d': 'Inscrição de vários atletas e categorias em um só pedido, paga com QR Code Pix e copia e cola próprios, sem login e sem gateway de pagamento de terceiros.',
    'ru.end': 'Quatro destes, e o sistema de 10 módulos, estão documentados no GitHub: o que construí, as ferramentas que escolhi e como cada um funciona.',
    'ru.gh': 'Conhecer meu GitHub',
    'ex.kind': 'Log de deploys · experiência', 'ex.title': 'Experiência',
    'ex.1.d': 'out 2026 → hoje', 'ex.1.r': '· AI Systems &amp; Automation Engineer, meio período',
    'ex.1.p': 'Remoto, para uma agência dos Estados Unidos.',
    'ex.2.d': 'out 2025 → hoje', 'ex.2.r': '· Consultor de IA e automação',
    'ex.2.p': 'Consultoria para mais de 20 clientes. Entendo como cada time trabalha, desenho a solução e implemento agentes e integrações para atendimento, qualificação de leads e vendas, com documentação para o time dar continuidade.',
    'ex.3.d': 'mar 2024 → out 2026', 'ex.3.r': '· Automação e soluções de IA',
    'ex.3.p': 'Liderei a equipe de tecnologia. Desenvolvi e mantive mais de 300 workflows com n8n, Python e JavaScript, agentes de pré-vendas para mais de 50 clínicas, integrações com CRMs e agendas, e uma solução de conteúdo que reduziu um ciclo de três dias para minutos.',
    'ex.4.d': 'jan → ago 2024', 'ex.4.r': '· Desenvolvedor de software',
    'ex.4.p': 'Uma plataforma de inscrições para torneios de beach tennis com React e Node.js, incluindo checkout e pagamento por Pix.',
    'ex.5.d': 'fev 2022 → mar 2023', 'ex.5.r': '· Desenvolvedor de software júnior',
    'ex.5.p': 'Um CRM interno de RH com interfaces React, dashboards e componentes reutilizáveis, e trabalho no Figma dos wireframes ao design system.',
    'ex.6.d': 'jan 2021 → jan 2022', 'ex.6.h': 'Autônomo <span>· Desenvolvimento de chatbots</span>',
    'ex.6.p': 'Bots para Discord em Python, com recursos de interação para comunidades online.',
    'sk.1': 'Automação e integrações', 'sk.2': 'IA aplicada',
    'sk.2.l': 'Agentes de IA · OpenAI · Google Gemini · Anthropic · RAG · Engenharia de prompts',
    'sk.3': 'Desenvolvimento, dados e DevOps', 'sk.4': 'Formação e idiomas',
    'sk.4.p': 'Análise e Desenvolvimento de Sistemas na UNIGRAN, em andamento. Português nativo, inglês avançado (C1, certificado EF SET).',
    'ou.kind': 'Saída · rascunho pronto', 'ou.state': 'editável', 'ou.to': 'Para', 'ou.subject': 'Assunto', 'ou.body': 'Mensagem',
    'ou.send': 'Abrir no app de e-mail', 'ou.copy': 'Copiar rascunho',
    'wa.send': 'Enviar no WhatsApp', 'wa.talk': 'Falar no WhatsApp',
    'ou.title': 'Se combina com o que você está construindo, o currículo completo está a um clique.',
    'ou.email': 'E-mail',
    'ou.foot': 'Tudo acima rodou no seu navegador. Sua mensagem não foi enviada para lugar nenhum.',
    'film.title': 'Apresentação · em inglês · 1:21', 'close': 'Fechar'
  };

  var DYN = {
    en: {
      sent: 'sent', waiting: 'waiting', matches: function (n) { return n + (n === 1 ? ' match' : ' matches'); },
      intent: { hiring: 'Hiring', project: 'Project', question: 'General question' },
      engagement: { full: 'Full-time', contract: 'Contract or part-time', project: 'Project-based', none: 'Not stated' },
      remote: { remote: 'Remote', onsite: 'On-site or hybrid', none: 'Not stated' },
      lang: { en: 'English', pt: 'Portuguese' },
      noFocus: 'Nothing specific yet: try naming a tool or a team',
      why: function (tags) { return tags.length ? tags.join(' · ') : 'General fit'; },
      log: [
        function (s) { return 'received <b>' + s.n + ' chars</b> · ' + s.langCode; },
        function (s) { return 'session <b>' + s.sid + '</b> · lead card linked'; },
        function (s) { return 'intent <b>' + s.intent + '</b> · queued'; },
        function (s) { return 'context <b>' + s.focusShort + '</b>'; },
        function () { return 'tools <b>Kommo MCP</b>, internal MCP'; },
        function () { return 'reply ready · <b>WhatsApp</b>'; },
        function (s) { return 'supervisor notified · ' + s.engagement; },
        function () { return 'knowledge base <b>updated</b>'; },
        function () { return 'session <b>reset</b>'; },
        function () { return 'human history <b>stored</b>'; }
      ],
      subject: { full: 'Full-time role: AI & automation', fullR: 'Full-time remote role: AI & automation', contract: 'Contract role: AI & automation', contractR: 'Remote contract role: AI & automation', project: 'Project inquiry: AI & automation', none: 'From your portfolio: AI & automation' },
      greet: 'Hi Thalyson,', stood: 'From your portfolio, these stood out:', sign: 'Best regards,',
      core: 'Core work · no topics found in your message', empty: 'Waiting for a message', zero: '0 matches',
      summary: function (a, b, c, n) { return 'Parsed: ' + a + ', ' + b + ', ' + c + '. ' + n + '.'; },
      copied: 'Draft copied.', copyFail: 'Select the text above to copy it.',
      samples: {
        full: "Hi Thalyson, we're hiring a remote AI automation engineer. You'd build AI agents and n8n workflows and connect our CRM and WhatsApp for the sales team. Full-time.",
        contract: 'Hi Thalyson, we need a contractor for about three months to automate our lead intake with AI agents, n8n and our CRM. Remote is fine.',
        project: 'Hi Thalyson, our clinic wants an AI agent on WhatsApp that answers patients, qualifies leads and books appointments in Google Calendar. Do you take on projects like this?'
      }
    },
    pt: {
      sent: 'enviada', waiting: 'aguardando', matches: function (n) { return n + (n === 1 ? ' resultado' : ' resultados'); },
      intent: { hiring: 'Contratação', project: 'Projeto', question: 'Pergunta geral' },
      engagement: { full: 'Tempo integral', contract: 'Contrato ou meio período', project: 'Por projeto', none: 'Não informado' },
      remote: { remote: 'Remoto', onsite: 'Presencial ou híbrido', none: 'Não informado' },
      lang: { en: 'Inglês', pt: 'Português' },
      noFocus: 'Nada específico ainda: tente citar uma ferramenta ou um time',
      why: function (tags) { return tags.length ? tags.join(' · ') : 'Encaixe geral'; },
      log: [
        function (s) { return 'recebido <b>' + s.n + ' caracteres</b> · ' + s.langCode; },
        function (s) { return 'sessão <b>' + s.sid + '</b> · card do lead vinculado'; },
        function (s) { return 'intenção <b>' + s.intent + '</b> · na fila'; },
        function (s) { return 'contexto <b>' + s.focusShort + '</b>'; },
        function () { return 'ferramentas <b>Kommo MCP</b>, MCP interno'; },
        function () { return 'resposta pronta · <b>WhatsApp</b>'; },
        function (s) { return 'supervisor avisado · ' + s.engagement; },
        function () { return 'base de conhecimento <b>atualizada</b>'; },
        function () { return 'sessão <b>reiniciada</b>'; },
        function () { return 'histórico humano <b>registrado</b>'; }
      ],
      subject: { full: 'Vaga em tempo integral: IA e automação', fullR: 'Vaga remota em tempo integral: IA e automação', contract: 'Vaga por contrato: IA e automação', contractR: 'Vaga remota por contrato: IA e automação', project: 'Proposta de projeto: IA e automação', none: 'Pelo seu portfólio: IA e automação' },
      greet: 'Oi, Thalyson,', stood: 'No seu portfólio, estes projetos chamaram minha atenção:', sign: 'Abraços,',
      core: 'Trabalho principal · nenhum tema encontrado na sua mensagem', empty: 'Aguardando uma mensagem', zero: '0 resultados',
      summary: function (a, b, c, n) { return 'Leitura: ' + a + ', ' + b + ', ' + c + '. ' + n + '.'; },
      copied: 'Rascunho copiado.', copyFail: 'Selecione o texto acima para copiar.',
      samples: {
        full: 'Oi, Thalyson! Estamos contratando um engenheiro de automação com IA para trabalho remoto. Você vai criar agentes de IA e workflows no n8n e integrar nosso CRM e o WhatsApp ao time comercial. Tempo integral.',
        contract: 'Oi, Thalyson! Precisamos de alguém por contrato, por cerca de três meses, para automatizar a entrada de leads com agentes de IA, n8n e nosso CRM. Pode ser remoto.',
        project: 'Oi, Thalyson! Nossa clínica quer um agente de IA no WhatsApp que responda pacientes, qualifique leads e marque consultas no Google Calendar. Você pega projetos assim?'
      }
    }
  };

  var FOCUS = [
    { id: 'agents', en: 'AI agents', pt: 'Agentes de IA', re: /\bagent|agente|chatbot|\bbots?\b|assistente|assistant/ },
    { id: 'ai', en: 'LLMs', pt: 'LLMs', re: /\bai\b|\bia\b|\bllms?\b|\bgpt|openai|claude|gemini|anthropic|inteligencia artificial|machine learning/ },
    { id: 'rag', en: 'RAG', pt: 'RAG', re: /\brag\b|retrieval|embedding|vector|base de conhecimento|knowledge base/ },
    { id: 'automation', en: 'n8n & automation', pt: 'n8n e automação', re: /automat|automac|workflow|\bn8n|zapier|make\.com|\bfluxos?\b/ },
    { id: 'integrations', en: 'Integrations & CRM', pt: 'Integrações e CRM', re: /integra|\bapis?\b|webhook|\bcrm|hubspot|kommo|gohighlevel|whatsapp|calendar|\bagenda|scheduling/ },
    { id: 'web', en: 'Web development', pt: 'Desenvolvimento web', re: /react|next\.?js|node|front-?end|back-?end|full-?stack|website|\bsites?\b|landing|typescript|javascript|\bweb\b|checkout/ },
    { id: 'data', en: 'Data & reporting', pt: 'Dados e relatórios', re: /supabase|postgres|\bsql\b|database|banco de dados|\bdados\b|\bdata\b|dashboard|report|relatorio|analytic|analise/ },
    { id: 'sales', en: 'Sales operations', pt: 'Operações comerciais', re: /\bsales\b|vendas|comercial|\bleads?\b|closer|pipeline|prospec/ },
    { id: 'health', en: 'Healthcare', pt: 'Saúde', re: /clinic|clinica|medic|health|saude|patient|paciente|consulta|appointment/ },
    { id: 'devops', en: 'DevOps', pt: 'DevOps', re: /docker|\baws\b|devops|server|servidor|deploy|infra|kubernetes|linux/ }
  ];
  var FOCUS_BY_ID = {}; FOCUS.forEach(function (f) { FOCUS_BY_ID[f.id] = f; });

  // the knowledge base: real projects and their topics
  var KB = [
    { id: 'clinic-agents', en: 'AI agents for medical clinics', pt: 'Agentes de IA para clínicas', tags: ['agents', 'ai', 'automation', 'integrations', 'health', 'sales'] },
    { id: 'cs-system', en: 'AI customer service system (10 modules)', pt: 'Sistema de atendimento com IA (10 módulos)', tags: ['agents', 'ai', 'rag', 'automation', 'integrations', 'health', 'devops'] },
    { id: 'sales-intel', en: 'Sales intelligence reports', pt: 'Relatórios de inteligência comercial', tags: ['sales', 'ai', 'automation', 'data', 'web', 'integrations'] },
    { id: 'wa-analytics', en: 'WhatsApp conversation analytics', pt: 'Inteligência de conversas de WhatsApp', tags: ['ai', 'data', 'health', 'integrations', 'web', 'automation', 'sales'] },
    { id: 'call-analysis', en: 'Sales call analysis', pt: 'Análise de calls comerciais', tags: ['sales', 'ai', 'data', 'automation'] },
    { id: 'everbetter', en: 'EverBetter', pt: 'EverBetter', tags: ['web', 'ai', 'data', 'devops'] },
    { id: 'landpages', en: 'Landpages', pt: 'Landpages', tags: ['web', 'devops', 'health'] },
    { id: 'pix-checkout', en: 'Pix checkout for a beach tennis tournament', pt: 'Checkout Pix para torneio de beach tennis', tags: ['web', 'data'] }
  ];

  /* ---------------------------------------------------------- parsing --- */
  function norm(t) { return (t || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); }

  function parse(text) {
    var t = norm(text);
    var intent = /hiring|\bhire\b|\brole\b|position|\bjob\b|vaga|contrata|recrut|opportunit|oportunidade|candidat|join our team|our team|contractor|freelancer|we need someone|precisamos de alguem|por contrato/.test(t) ? 'hiring'
      : /project|projeto|build|criar|automate|automatizar|quote|orcamento|proposta|freela/.test(t) ? 'project' : 'question';
    var engagement = /full[- ]?time|tempo integral|\bclt\b|efetiv|permanent/.test(t) ? 'full'
      : /part[- ]?time|contract|contrato|\bpj\b|meio periodo|months|meses/.test(t) ? 'contract'
      : /freelanc|project|projeto|one-off|pontual/.test(t) ? 'project' : 'none';
    var remote = /remote|remot|home office|anywhere|qualquer lugar/.test(t) ? 'remote'
      : /on[- ]?site|presencial|hybrid|hibrid|in the office|no escritorio/.test(t) ? 'onsite' : 'none';
    var ptHits = (t.match(/\b(nos|nossa|nosso|voce|para|com|uma|um|que|estamos|precisamos|vaga|time|clinica)\b/g) || []).length;
    var enHits = (t.match(/\b(we|our|you|the|and|with|for|are|need|team|role|hiring)\b/g) || []).length;
    var lang = ptHits > enHits ? 'pt' : 'en';
    var focus = FOCUS.filter(function (f) { return f.re.test(t); }).map(function (f) { return f.id; });
    return { intent: intent, engagement: engagement, remote: remote, lang: lang, focus: focus, n: (text || '').length };
  }

  function rank(parsed) {
    if (!parsed.focus.length) {
      return KB.map(function (item) { return { item: item, hit: [], score: 0, core: true }; });
    }
    var q = parsed.focus;
    return KB.map(function (item) {
      var hit = item.tags.filter(function (tag) { return q.indexOf(tag) > -1; });
      var score = hit.length / Math.max(q.length, 1);
      return { item: item, hit: hit, score: Math.round(score * 100) / 100 };
    }).sort(function (a, b) { return b.score - a.score || b.hit.length - a.hit.length; });
  }

  function hash4(s) {
    var h = 2166136261;
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return ('0000' + (h >>> 0).toString(16)).slice(-4);
  }

  /* ------------------------------------------------------------ state --- */
  var state = {
    lang: store('tedsp-language') === 'pt' ? 'pt' : 'en',
    preset: 'full', edited: false, draftDirty: false,
    parsed: null, ranked: null
  };
  var summaryT;
  var WA = 'https://wa.me/5567984732575';
  var payload = $('#payload');
  var draft = $('#draft');
  var subject = $('#subject');

  /* ------------------------------------------------------------- i18n --- */
  var EN = {};
  $$('[data-i18n]').forEach(function (el) { EN[el.getAttribute('data-i18n')] = el.innerHTML; });
  $$('[data-i18n-attr]').forEach(function (el) {
    el.getAttribute('data-i18n-attr').split(';').forEach(function (pair) {
      var kv = pair.split(':'); EN[kv[1]] = el.getAttribute(kv[0]);
    });
  });

  function applyLang(lang) {
    state.lang = lang;
    var dict = lang === 'pt' ? PT : EN;
    document.documentElement.lang = lang === 'pt' ? 'pt-BR' : 'en';
    $$('[data-i18n]').forEach(function (el) {
      var k = el.getAttribute('data-i18n'); var v = dict[k] != null ? dict[k] : EN[k];
      if (v != null && el.innerHTML !== v) el.innerHTML = v;
    });
    $$('[data-i18n-attr]').forEach(function (el) {
      el.getAttribute('data-i18n-attr').split(';').forEach(function (pair) {
        var kv = pair.split(':'); var v = dict[kv[1]] != null ? dict[kv[1]] : EN[kv[1]];
        if (v != null) el.setAttribute(kv[0], v);
      });
    });
    $$('[data-lang]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-lang') === lang)); });
    $$('[data-cv]').forEach(function (a) { a.href = 'assets/thalyson-emanuel-cv-' + lang + '.pdf'; });
    var waHello = lang === 'pt' ? 'Oi, Thalyson! Vi seu portfólio e gostaria de conversar.' : 'Hi Thalyson, I saw your portfolio and would like to talk.';
    $$('[data-wa]').forEach(function (a) { a.href = WA + '?text=' + encodeURIComponent(waHello); });
    document.title = lang === 'pt' ? 'Thalyson Emanuel · Desenvolvedor de IA e Automação' : 'Thalyson Emanuel · AI & Automation Developer';
    if (!state.edited) { payload.value = DYN[lang].samples[state.preset]; state.draftDirty = false; }
    store('tedsp-language', lang);
    var prevIdx = Math.max(current, 0);
    current = -1;
    if (statusNode) statusNode.textContent = (lang === 'pt' ? PT : EN)['n.' + nodes[prevIdx]];
    // stack lines: keep each item whole so a wrapped line never starts with a dot
    $$('.stack').forEach(function (el) {
      if (el.querySelector('.si')) return;
      var parts = el.textContent.split(' · ');
      el.innerHTML = '';
      parts.forEach(function (t, i) {
        var sp = document.createElement('span'); sp.className = 'si';
        sp.textContent = t + (i < parts.length - 1 ? ' ·' : '');
        el.appendChild(sp);
        if (i < parts.length - 1) el.appendChild(document.createTextNode(' '));
      });
    });
    run();
    requestAnimationFrame(measure);
  }

  /* ---------------------------------------------------------- rendering - */
  function focusLabels(ids) { return ids.map(function (id) { return FOCUS_BY_ID[id][state.lang]; }); }

  function run() {
    var d = DYN[state.lang];
    var p = state.parsed = parse(payload.value);
    var r = state.ranked = rank(p);

    // inspector + status
    $('[data-insp-len]').textContent = p.n;
    $('[data-insp-lang]').textContent = p.lang;
    var raw = payload.value.trim();
    $('[data-status-payload]').textContent = raw ? '“' + raw.slice(0, 90) + (raw.length > 90 ? '…' : '') + '”' : d.empty;

    // classify
    $('[data-echo]').textContent = raw ? (raw.length > 150 ? raw.slice(0, 150) + '…' : raw) : d.empty;
    $('[data-out="intent"]').textContent = d.intent[p.intent];
    $('[data-out="engagement"]').textContent = d.engagement[p.engagement];
    $('[data-out="remote"]').textContent = d.remote[p.remote];
    $('[data-out="lang"]').textContent = d.lang[p.lang];
    var chips = $('[data-out="focus"]');
    chips.innerHTML = '';
    if (p.focus.length) {
      chips.classList.remove('chips--plain');
      focusLabels(p.focus).forEach(function (l) { var li = document.createElement('li'); li.textContent = l; chips.appendChild(li); });
    } else {
      chips.classList.add('chips--plain');
      var li = document.createElement('li'); li.textContent = d.noFocus; chips.appendChild(li);
    }

    // retrieve: top three
    var top = r.slice(0, 3);
    var list = $('[data-matches]'); list.innerHTML = '';
    top.forEach(function (m) {
      var li = document.createElement('li'); li.className = 'match';
      var b = document.createElement('b'); b.textContent = m.item[state.lang];
      var s = document.createElement('span'); s.className = 'score'; s.textContent = m.core ? '' : m.score.toLocaleString(state.lang === 'pt' ? 'pt-BR' : 'en', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      var bar = document.createElement('span'); bar.className = 'bar'; var i = document.createElement('i'); i.style.setProperty('--s', String(m.score)); bar.appendChild(i);
      var why = document.createElement('span'); why.className = 'why'; why.textContent = m.core ? d.core : d.why(focusLabels(m.hit));
      li.appendChild(b); li.appendChild(s); li.appendChild(bar); li.appendChild(why); list.appendChild(li);
    });
    var strong = r.filter(function (m) { return m.score > 0; });
    var nMatch = Math.min(strong.length, 3);
    $('[data-match-count]').textContent = nMatch ? d.matches(nMatch) : d.zero;
    clearTimeout(summaryT);
    summaryT = setTimeout(function () {
      $('[data-run-summary]').textContent = d.summary(d.intent[p.intent], d.engagement[p.engagement], d.remote[p.remote], nMatch ? d.matches(nMatch) : d.zero);
    }, 700);

    // runs: flag the top matches that are run cards
    var flagged = top.filter(function (m) { return m.score > 0; }).map(function (m) { return m.item.id; });
    $$('[data-run]').forEach(function (el) {
      if (flagged.indexOf(el.getAttribute('data-run')) > -1) el.setAttribute('data-match', ''); else el.removeAttribute('data-match');
    });

    // system log lines
    var s = {
      n: p.n, langCode: p.lang, sid: hash4(payload.value), intent: d.intent[p.intent].toLowerCase(),
      engagement: d.engagement[p.engagement].toLowerCase(),
      focusShort: focusLabels(p.focus).slice(0, 2).join(', ') || d.intent[p.intent]
    };
    var log = $('[data-log]'); log.innerHTML = '';
    d.log.forEach(function (fn, k) {
      var li = document.createElement('li');
      li.innerHTML = '<time>' + (k < 9 ? '0' : '') + (k + 1) + '</time><span>' + fn(s) + '</span>';
      log.appendChild(li);
    });
    lastLit = -1;

    // output
    if (!state.draftDirty) composeDraft();
    updateSend();
  }

  function composeDraft() {
    var p = state.parsed;
    var dl = payload.value.trim() ? p.lang : state.lang;     // the email speaks the message's language
    var d = DYN[dl];
    var msg = payload.value.trim();
    var greetFirst = /^(hi|hello|hey|dear|oi|ola|bom dia|boa tarde)\b/.test(norm(msg)) ? '' : d.greet + '\n\n';
    var picks = state.ranked.slice(0, 3).filter(function (m) { return m.score > 0; }).map(function (m) { return '- ' + m.item[dl]; });
    var key = p.engagement !== 'none' ? p.engagement : (p.intent === 'project' ? 'project' : 'none');
    if ((key === 'full' || key === 'contract') && p.remote === 'remote') key += 'R';
    subject.value = d.subject[key] || d.subject.none;
    draft.value = greetFirst + (msg ? msg + '\n\n' : '') + (picks.length ? d.stood + '\n' + picks.join('\n') + '\n\n' : '') + d.sign + '\n';
  }

  function updateSend() {
    $('[data-wa-draft]').href = WA + '?text=' + encodeURIComponent(draft.value.trim());
    var a = $('[data-send]');
    a.href = 'mailto:thalysonemanuels.p@gmail.com?subject=' + encodeURIComponent(subject.value) + '&body=' + encodeURIComponent(draft.value);
  }

  /* ------------------------------------------------------------ events --- */
  payload.addEventListener('input', function () {
    state.edited = true; state.draftDirty = false;
    $$('[data-preset]').forEach(function (b) { b.setAttribute('aria-pressed', 'false'); });
    run();
  });
  $$('[data-preset]').forEach(function (b) {
    b.addEventListener('click', function () {
      var key = b.getAttribute('data-preset');
      if (key === state.preset && !state.edited && payload.value === DYN[state.lang].samples[key]) return;
      state.preset = key; state.edited = false; state.draftDirty = false;
      $$('[data-preset]').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      payload.value = DYN[state.lang].samples[state.preset];
      run();
    });
  });
  draft.addEventListener('input', function () { state.draftDirty = true; updateSend(); });
  subject.addEventListener('input', function () { state.draftDirty = true; updateSend(); });
  $$('[data-lang]').forEach(function (b) { b.addEventListener('click', function () { applyLang(b.getAttribute('data-lang')); }); });

  $$('[data-js-only]').forEach(function (el) { el.hidden = false; });

  var toast = $('[data-toast]'); var toastT;
  $('[data-copy-draft]').addEventListener('click', function () {
    var text = subject.value + '\n\n' + draft.value;
    var done = function (ok) {
      toast.textContent = ok ? DYN[state.lang].copied : DYN[state.lang].copyFail;
      clearTimeout(toastT); toastT = setTimeout(function () { toast.textContent = ''; }, 2600);
      if (!ok) { draft.focus(); draft.select(); }
    };
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); });
    else done(false);
  });

  var film = $('dialog.film'); var filmVideo = film.querySelector('video');
  $('[data-open-film]').addEventListener('click', function () {
    if (typeof film.showModal === 'function') film.showModal(); else window.open('assets/intro-en.mp4', '_blank');
    var track = filmVideo.textTracks && filmVideo.textTracks[0];
    if (track) track.mode = state.lang === 'pt' ? 'showing' : 'disabled';
  });
  $('[data-close-film]').addEventListener('click', function () { film.close(); });
  film.addEventListener('close', function () { filmVideo.pause(); });
  film.addEventListener('click', function (e) { if (e.target === film) film.close(); });

  /* -------------------------------------------------------- geometry ---- */
  var entry = $('#trigger'), entryPad = entry.querySelector('.stage-pad'), entryStage = entry.querySelector('[data-sc-stage]');
  var trig = $('[data-trigger]'), trigState = $('[data-trigger-state]');
  var ew = $('[data-entry-wire]'), ewBase = ew.querySelector('.base'), ewLive = ew.querySelector('.live'), ewTok = ew.querySelector('.token'), ewPort = ew.querySelector('.port');
  var ewLen = 1;

  var sys = $('#system'), sysStage = sys.querySelector('[data-sc-stage]');
  var map = $('[data-map]'), mods = $$('.mod', map), wires = map.querySelector('.map__wires');
  var wBase = wires.querySelector('.base'), wLive = wires.querySelector('.live'), wTok = wires.querySelector('.token');
  var services = $$('.services li', map);
  var pathLen = 1, cum = [];

  function measure() {
    // entry wire: from the trigger's bottom edge down out of the frame
    var pr = entryPad.getBoundingClientRect(), tr = trig.getBoundingClientRect();
    var x = Math.round(tr.left - pr.left + tr.width * 0.18), y0 = Math.round(tr.bottom - pr.top), y1 = Math.round(pr.height - 18);
    var dEntry = 'M' + x + ' ' + y0 + ' V' + y1;
    ewBase.setAttribute('d', dEntry); ewLive.setAttribute('d', dEntry);
    ewLen = Math.max(1, y1 - y0);
    ewPort.setAttribute('cx', x); ewPort.setAttribute('cy', y1);
    ewLive.style.strokeDasharray = ewLen + ' ' + ewLen;

    // system map: one orthogonal route through every module centre
    var mr = map.getBoundingClientRect();
    var pts = mods.map(function (m) { var r = m.getBoundingClientRect(); return [r.left - mr.left + r.width / 2, r.top - mr.top + r.height / 2]; });
    var d = 'M' + pts[0][0].toFixed(1) + ' ' + pts[0][1].toFixed(1);
    cum = [0]; var total = 0;
    for (var i = 1; i < pts.length; i++) {
      var a = pts[i - 1], b = pts[i];
      var dx = Math.abs(b[0] - a[0]), dy = Math.abs(b[1] - a[1]);
      if (dx > 2 && dy > 2) { d += ' H' + b[0].toFixed(1) + ' V' + b[1].toFixed(1); }
      else d += ' L' + b[0].toFixed(1) + ' ' + b[1].toFixed(1);
      total += dx + dy; cum.push(total);
    }
    wBase.setAttribute('d', d); wLive.setAttribute('d', d);
    pathLen = Math.max(1, total);
    wLive.style.strokeDasharray = pathLen + ' ' + pathLen;
    lastLit = -2; lastHp = -1; lastT = -1;
  }

  /* ------------------------------------------------------- frame loop --- */
  var nodes = ['trigger', 'classify', 'retrieve', 'system', 'runs', 'experience', 'output'];
  var sections = nodes.map(function (n) { return document.getElementById(n); });
  var navLinks = $$('[data-node]');
  var statusNode = $('[data-status-node]');
  var current = -1, lastHp = -1, lastT = -1, lastLit = -1;
  var mx = 0, my = 0, tmx = 0, tmy = 0;

  function actP(el) { var v = parseFloat(el.style.getPropertyValue('--sc-p')); return isNaN(v) ? 0 : v; }

  function frame() {
    var vh = innerHeight;

    // which node is running
    var idx = 0;
    for (var i = 0; i < sections.length; i++) { if (sections[i].getBoundingClientRect().top <= vh * 0.45) idx = i; }
    if (innerHeight + scrollY >= document.documentElement.scrollHeight - 4) idx = sections.length - 1;
    if (idx !== current) {
      current = idx;
      navLinks.forEach(function (a) {
        var k = nodes.indexOf(a.getAttribute('data-node'));
        a.setAttribute('data-state', k < idx ? 'done' : k === idx ? 'run' : 'idle');
        if (k === idx) a.setAttribute('aria-current', 'step'); else a.removeAttribute('aria-current');
      });
      statusNode.textContent = (state.lang === 'pt' ? PT : EN)['n.' + nodes[idx]];
      var tab = $('.tabs [data-node="' + nodes[idx] + '"]');
      var strip = tab && tab.closest('.tabs');
      if (strip && strip.scrollWidth > strip.clientWidth) {
        var li = tab.parentNode;
        var left = li.getBoundingClientRect().left - strip.getBoundingClientRect().left + strip.scrollLeft - 12;
        strip.scrollTo({ left: Math.max(0, left), behavior: reduced ? 'auto' : 'smooth' });
      }
    }

    // act 1: the trigger sends
    var hp = actP(entry);
    if (Math.abs(hp - lastHp) > 0.002) {
      lastHp = hp;
      entryPad.style.setProperty('--hp', hp.toFixed(3));
      var send = clamp01((hp - 0.12) / 0.7);
      ewLive.style.strokeDashoffset = String(ewLen * (1 - send));
      if (!reduced && send > 0 && send < 1) {
        var pt = ewLive.getPointAtLength(ewLen * send);
        ewTok.setAttribute('cx', pt.x); ewTok.setAttribute('cy', pt.y); ewTok.setAttribute('opacity', '1');
      } else ewTok.setAttribute('opacity', '0');
      ewPort.setAttribute('stroke', send >= 0.999 ? '#5b8cff' : '#1d2c4c');
      var isSent = send > 0.04;
      if (isSent) trigState.setAttribute('data-on', ''); else trigState.removeAttribute('data-on');
      trigState.lastChild.textContent = isSent ? DYN[state.lang].sent : DYN[state.lang].waiting;
      entryStage.setAttribute('data-sc-verify-state', String(Math.round(send * 24)));
    }

    // act 4: the system runs
    var t = clamp01((actP(sys) - 0.05) / 0.82);
    if (Math.abs(t - lastT) > 0.001 || lastLit === -2) {
      lastT = t;
      var at = pathLen * t;
      wLive.style.strokeDashoffset = String(pathLen * (1 - t));
      if (!reduced && t > 0 && t < 1) {
        var q = wLive.getPointAtLength(at);
        wTok.setAttribute('cx', q.x); wTok.setAttribute('cy', q.y); wTok.style.opacity = '1';
      } else wTok.style.opacity = '0';
      var lit = -1;
      for (var k = 0; k < cum.length; k++) { if (at >= cum[k] - 0.5 && t > 0) lit = k; }
      if (lit !== lastLit) {
        lastLit = lit;
        mods.forEach(function (m, j) {
          if (j <= lit) m.setAttribute('data-lit', ''); else m.removeAttribute('data-lit');
          if (j === lit) m.setAttribute('data-now', ''); else m.removeAttribute('data-now');
        });
        var lines = $$('[data-log] li');
        lines.forEach(function (li, j) {
          if (j <= lit) li.setAttribute('data-on', ''); else li.removeAttribute('data-on');
          li.classList.toggle('tail', j <= lit && j > lit - (innerHeight <= 700 ? 2 : 3));
        });
        $('[data-exec-state]').textContent = (lit + 1) + ' / 10';
      }
      var sLit = Math.round(services.length * t);
      services.forEach(function (s, j) { if (j < sLit) s.setAttribute('data-lit', ''); else s.removeAttribute('data-lit'); });
      sysStage.style.setProperty('--t', t.toFixed(3));
      sysStage.setAttribute('data-sc-verify-state', String(Math.round(t * 40)));
      if (t >= 1) sysStage.setAttribute('data-sc-verify-hold', 'true'); else sysStage.removeAttribute('data-sc-verify-hold');
    }

    // pointer depth on the entry planes
    if (finePointer && !reduced) {
      mx += (tmx - mx) * 0.08; my += (tmy - my) * 0.08;
      if (Math.abs(tmx - mx) > 0.001 || Math.abs(tmy - my) > 0.001) {
        entryPad.style.setProperty('--mx', mx.toFixed(3)); entryPad.style.setProperty('--my', my.toFixed(3));
      }
    }
    requestAnimationFrame(frame);
  }

  if (finePointer && !reduced) {
    addEventListener('pointermove', function (e) {
      var r = entryPad.getBoundingClientRect();
      if (r.bottom < 0 || r.top > innerHeight) return;
      tmx = ((e.clientX - r.left) / r.width - 0.5) * 2;
      tmy = ((e.clientY - r.top) / r.height - 0.5) * 2;
    }, { passive: true });
  }

  /* ------------------------------------------------------------ focus --- */
  var runs = $('#runs'), rail = $('.rail', runs), runsStage = runs.querySelector('[data-sc-stage]');
  rail.addEventListener('focusin', function (e) {
    if (reduced) return;
    var card = e.target.closest('.rail > *'); if (!card) return;
    var over = rail.scrollWidth - innerWidth; if (over <= 0) return;
    var side = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--side')) || 0;
    var x = card.offsetLeft + card.offsetWidth / 2 - (innerWidth - side) / 2;
    var pTarget = clamp01(x / over);
    var top = runs.getBoundingClientRect().top + scrollY;
    scrollTo({ top: Math.round(top + pTarget * (runs.offsetHeight - innerHeight)), behavior: 'instant' });
  });
  if (reduced) {
    EN.runsRegion = 'Runs, scroll sideways'; PT.runsRegion = 'Execuções, role para o lado';
    runsStage.setAttribute('tabindex', '0'); runsStage.setAttribute('role', 'region');
    runsStage.setAttribute('aria-label', EN.runsRegion); runsStage.setAttribute('data-i18n-attr', 'aria-label:runsRegion');
  }
  $$('.tabs a').forEach(function (a) {
    a.addEventListener('focus', function () { a.scrollIntoView({ inline: 'nearest', block: 'nearest' }); });
  });

  /* ------------------------------------------------------------- boot --- */
  if (window.ResizeObserver) { var ro = new ResizeObserver(function () { measure(); }); ro.observe(map); ro.observe(trig); ro.observe(entryPad); }
  addEventListener('resize', measure);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { measure(); if (sc && sc.layout) sc.layout(); });

  applyLang(state.lang);
  measure();
  requestAnimationFrame(frame);
})();
