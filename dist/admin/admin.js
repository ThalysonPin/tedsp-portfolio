'use strict';

const app = document.getElementById('app');
const dialog = document.getElementById('editor');
const editorForm = document.getElementById('editor-form');
let state = {session:null, content:null, revision:null, issues:[], page:'profile', lang:'pt', dirty:false};
let editorCommit = null;
let toastTimer;
const copy = value => JSON.parse(JSON.stringify(value));
const siteUrl = value => new URL(value || '/', location.origin + '/').href;
const localized = (value, lang = state.lang) => typeof value === 'object' && value !== null ? value[lang] || '' : value || '';
const langs = {pt:'Português',en:'English'};
const navItems = [['profile','Perfil e contato'],['texts','Textos PT / EN'],['jobs','Experiências'],['projects','Projetos'],['skills','Competências'],['files','Foto e currículos'],['theme','Cores e temas'],['security','Acesso e senha'],['advanced','Conteúdo completo']];

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key,value] of Object.entries(attrs)) {
    if (key.startsWith('on')) node.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key === 'checked' || key === 'disabled') node[key] = value;
    else node.setAttribute(key, value);
  }
  children.flat().forEach(child => {if (child !== null && child !== undefined) node.append(child instanceof Node ? child : document.createTextNode(String(child)));});
  return node;
}
function button(label, action, variant = '', attrs = {}) { return el('button',{type:'button',class:'button '+variant,onClick:action,...attrs},label); }
function notify(message, fail = false) {
  const toast = document.getElementById('toast'); toast.textContent = message; toast.className = 'toast'+(fail?' fail':''); toast.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(()=>toast.hidden=true,6500);
}
function markDirty() {state.dirty=true; updateSaveState();}
function updateSaveState() {
  const label = document.getElementById('save-state');
  if (label) {label.textContent=state.dirty?'Alterações no rascunho · ainda não publicadas':'Conteúdo publicado · revisão '+state.revision; label.classList.toggle('dirty',state.dirty);}
  const save = document.getElementById('publish'); if(save) save.disabled=!state.dirty;
}
async function api(path, options = {}) {
  const headers = {...options.headers};
  if (options.body && typeof options.body === 'string') headers['Content-Type']='application/json';
  if (state.session?.csrf) headers['X-CSRF-Token']=state.session.csrf;
  const response=await fetch('/api/admin/'+path,{credentials:'same-origin',cache:'no-store',...options,headers});
  const data=await response.json().catch(()=>({error:'Resposta inválida do servidor.'}));
  if (!response.ok) {
    const error=new Error(data.error || 'Não foi possível concluir a operação.'); error.status=response.status;
    if(response.status===401 && state.session?.authenticated) {state.session.authenticated=false; state.content=null; renderAuth('Sua sessão expirou. Entre novamente.');}
    throw error;
  }
  return data;
}
function jsonRequest(path, body, method='POST') {return api(path,{method,body:JSON.stringify(body)});}
function field(label, value, change, options = {}) {
  const id='f-'+(++field.count); const type=options.type || 'text';
  const input=el(options.multiline?'textarea':options.select?'select':'input',{id,...(!options.multiline&&!options.select?{type}:{}),...(options.attrs||{})});
  if(options.select) options.select.forEach(([val,name])=>input.append(el('option',{value:val},name)));
  input.value=value ?? '';
  input.addEventListener(options.select?'change':'input',()=>change(input.value,input));
  const box=el('div',{class:'field'+(options.full?' full':'')},el('label',{for:id},label),input);
  if(options.help) box.append(el('p',{class:'help'},options.help));
  return box;
}
field.count=0;
function draftField(label,obj,key,options={}) {return field(label,obj[key],value=>{obj[key]=value;markDirty();},options);}
function listValue(text) {return text.split(',').map(x=>x.trim()).filter(Boolean);}
function linesValue(text) {return text.split('\n').map(x=>x.trim()).filter(Boolean);}
function bilingualFields(obj, keys) {
  return el('div',{class:'bilingual'},Object.entries(langs).map(([lang,label])=>el('div',{},el('p',{class:'lang-heading'},label),keys.map(({key,label:caption,multiline,help})=>field(caption,obj[key]?.[lang] || '',value=>{obj[key]??={pt:'',en:''};obj[key][lang]=value;},{multiline,help})))));
}
function beginEditor(title, nodes, commit) {
  document.getElementById('editor-title').textContent=title; document.getElementById('editor-fields').replaceChildren(...nodes);
  document.getElementById('editor-error').textContent=''; editorCommit=commit; dialog.showModal();
}
editorForm.addEventListener('submit',event=>{event.preventDefault();try{editorCommit?.();markDirty();dialog.close();renderPage();notify('Alteração aplicada ao rascunho. Publique quando terminar.');}catch(error){document.getElementById('editor-error').textContent=error.message;}});
document.getElementById('editor-close').addEventListener('click',()=>dialog.close());
document.getElementById('editor-cancel').addEventListener('click',()=>dialog.close());
window.addEventListener('beforeunload',event=>{if(state.dirty){event.preventDefault();event.returnValue='';}});

async function start() {
  try {
    state.session=await api('session');
    if(state.session.authenticated) await loadContent(); else renderAuth();
  } catch(error) {renderAuth('Não foi possível acessar o painel. '+error.message);}
}
function renderAuth(message='') {
  const setup=state.session?.setupRequired;
  const available=state.session?.setupAvailable;
  const story=el('aside',{class:'auth-story'},el('span',{class:'brand'},'t.',el('small',{},'TEDSP / ADMIN')),el('div',{},el('span',{class:'eyebrow'},'GESTÃO DO PORTFÓLIO'),el('h1',{},'Atualize seu portfólio.'),el('p',{},'Edite textos, experiências, projetos, arquivos e identidade visual.')),el('small',{},'Thalyson Emanuel · Área administrativa'));
  const card=el('section',{class:'auth-card'},el('span',{class:'eyebrow'},setup?'PRIMEIRO ACESSO':'ACESSO RESTRITO'),el('h2',{},setup?'Defina sua senha':'Entre no painel'),el('p',{},setup?'Use o código de configuração para criar seu acesso de administrador.':'Use seu e-mail de administrador e sua senha.'));
  const form=el('form');
  const data={email:state.session?.email || 'thalysonemanuels.p@gmail.com',password:'',confirm:'',token:''};
  form.append(field('E-mail',data.email,value=>data.email=value,{type:'email',attrs:{autocomplete:'username',required:''}}));
  if(setup) {
    if(!available) card.append(el('div',{class:'notice warning'},'O primeiro acesso ainda precisa ser habilitado no servidor. Configure ADMIN_SETUP_TOKEN no Coolify e faça o deploy. Depois, use esse código aqui para definir sua senha.'));
    form.append(field('Código de configuração',data.token,value=>data.token=value,{type:'password',attrs:{autocomplete:'off',required:''},help:'Código ADMIN_SETUP_TOKEN configurado no Coolify. Usado apenas no primeiro acesso.'}));
  }
  form.append(field(setup?'Nova senha':'Senha',data.password,value=>data.password=value,{type:'password',attrs:{autocomplete:setup?'new-password':'current-password',required:'',minlength:setup?'12':'1'},help:setup?'Use pelo menos 12 caracteres.':undefined}));
  if(setup) form.append(field('Confirme a senha',data.confirm,value=>data.confirm=value,{type:'password',attrs:{autocomplete:'new-password',required:'',minlength:'12'}}));
  const errorNode=el('p',{class:'error',role:'alert'},message);
  const submit=el('button',{class:'button',type:'submit',disabled:!!setup&&!available},setup?'Criar acesso':'Entrar');
  form.append(errorNode,submit);
  form.addEventListener('submit',async event=>{
    event.preventDefault();errorNode.textContent='';
    if(setup&&data.password!==data.confirm){errorNode.textContent='As senhas não coincidem.';return;}
    submit.disabled=true;
    try{await jsonRequest(setup?'setup':'login',setup?{email:data.email.trim(),password:data.password,token:data.token.trim()}:{email:data.email.trim(),password:data.password});data.password='';data.confirm='';data.token='';state.session=await api('session');await loadContent();}
    catch(error){errorNode.textContent=error.message;submit.disabled=false;}
  });
  card.append(form,el('p',{class:'minor',style:'margin-top:24px'},el('a',{href:'/'},'← Voltar ao portfólio')));
  app.replaceChildren(el('main',{id:'main',class:'auth'},story,el('div',{class:'auth-card-wrap'},card)));
}
async function loadContent() {
  const [content,issues]=await Promise.all([api('content'),api('issue-projects')]);
  state.content=content.content;state.revision=content.revision;state.issues=Array.isArray(issues)?issues:issues.projects||[];state.dirty=false;
  renderShell();
}
function renderShell() {
  const sidebar=el('aside',{class:'sidebar'},el('span',{class:'brand'},'t.',el('small',{},'TEDSP / ADMIN')));
  const nav=el('nav',{'aria-label':'Seções de administração'});
  navItems.forEach(([key,label],i)=>nav.append(el('button',{class:'nav-button'+(state.page===key?' active':''),type:'button','data-page':key,onClick:()=>{state.page=key;renderPage();}},el('span',{},String(i+1).padStart(2,'0')),label)));
  sidebar.append(nav,el('div',{class:'sidebar-bottom'},el('p',{},state.session.email),el('p',{},'Alterações salvas aqui aparecem no site ao publicar.'),el('a',{href:'/',target:'_blank',rel:'noopener'},'Abrir portfólio ↗')));
  const lang=el('select',{class:'language-select','aria-label':'Idioma do conteúdo',onChange:event=>{state.lang=event.target.value;renderPage();}},el('option',{value:'pt'},'Conteúdo PT'),el('option',{value:'en'},'Conteúdo EN'));lang.value=state.lang;
  const top=el('header',{class:'topbar'},el('div',{},el('h1',{},'Administração do portfólio'),el('div',{id:'save-state',class:'save-state'})),el('div',{class:'top-actions'},lang,el('a',{class:'button secondary',href:'/',target:'_blank',rel:'noopener'},'Ver site ↗'),button('Salvar e publicar',publish,'',{id:'publish'})));
  app.replaceChildren(el('div',{class:'shell'},sidebar,el('div',{class:'workspace'},top,el('main',{id:'main',class:'content'}))));renderPage();
}
function pageHeader(title,description,action) {
  return el('div',{class:'page-heading'},el('div',{},el('span',{class:'eyebrow'},'GERENCIAR PORTFÓLIO'),el('h2',{},title),el('p',{},description)),action||null);
}
function panel(title,...nodes) {return el('section',{class:'panel'},title?el('h3',{},title):null,...nodes);}
function renderPage() {
  if(!state.content)return;
  document.querySelectorAll('.nav-button').forEach(b=>{b.classList.toggle('active',b.dataset.page===state.page);b.setAttribute('aria-current',b.dataset.page===state.page?'page':'false');});
  const main=document.getElementById('main');main.replaceChildren();
  ({profile:renderProfile,texts:renderTexts,jobs:renderJobs,projects:renderProjects,skills:renderSkills,files:renderFiles,theme:renderTheme,security:renderSecurity,advanced:renderAdvanced}[state.page]||renderProfile)(main);
  updateSaveState();
}
async function publish() {
  const save=document.getElementById('publish');save.disabled=true;save.textContent='Publicando…';
  try {const result=await jsonRequest('content',{content:state.content,revision:state.revision},'PUT');state.revision=result.revision; if(result.content)state.content=result.content;state.dirty=false;renderPage();notify('Alterações publicadas. O portfólio já está atualizado.');}
  catch(error){
    if(error.status===409){notify('O conteúdo foi atualizado em outro acesso. Exporte seu rascunho antes de recarregar.',true);if(confirm('Outro acesso publicou alterações. Deseja descartar seu rascunho e carregar a versão mais recente?'))await loadContent();}
    else notify(error.message,true);
  } finally {const current=document.getElementById('publish');if(current){current.textContent='Salvar e publicar';updateSaveState();}}
}
function renderProfile(main) {
  const p=state.content.profile;
  main.append(pageHeader('Perfil e contato','Atualize como você se apresenta e por onde as pessoas podem entrar em contato.'));
  main.append(panel('Identidade',el('div',{class:'form-grid'},draftField('Nome',p,'name'),draftField('Nome da marca',p,'brand'),draftField('Símbolo da marca',p,'brandMark'),draftField('Texto do rodapé',p,'footer'),draftField('Descrição da foto',p,'photoAlt',{full:true}))));
  main.append(panel('Contato',el('div',{class:'form-grid'},draftField('E-mail público',p,'email',{type:'email'}),draftField('WhatsApp · link completo',p,'whatsapp',{type:'url',help:'Exemplo: https://wa.me/5567984732575'}),draftField('LinkedIn',p,'linkedin',{type:'url'}),draftField('GitHub',p,'github',{type:'url'}))));
  main.append(panel('Números em destaque',el('div',{class:'form-grid'},p.metrics.map((value,i)=>field('Indicador '+(i+1),value,text=>{p.metrics[i]=text;markDirty();},{help:'A legenda de cada indicador está em Textos PT / EN.'})))));
}
const textNames={heroRole:'Cargo no início',heroIntro:'Apresentação',heroEyebrow:'Linha acima do nome',location:'Localização e modalidade',english:'Nível de inglês',metaDescription:'Descrição para buscadores',educationTitle:'Curso',educationSchool:'Instituição',languageDescription:'Idiomas e certificação',metric1:'Legenda do indicador 1',metric2:'Legenda do indicador 2',metric3:'Legenda do indicador 3',issuesTitle:'Título · projetos no GitHub',issuesIntro:'Introdução · projetos no GitHub',projectsTitle:'Título · projetos de IA',projectsIntro:'Introdução · projetos de IA',experienceTitle:'Título · experiência',experienceIntro:'Introdução · experiência',contactTitle:'Título · contato',contactIntro:'Apresentação · contato',skillsTitle:'Título · competências',skillsIntro:'Introdução · competências'};
function renderTexts(main) {
  main.append(pageHeader('Textos do site','Edite o conteúdo em '+langs[state.lang]+'. Use o seletor no topo para revisar o outro idioma.'));
  main.append(el('div',{class:'notice',style:'margin-bottom:22px'},'Você pode usar <br>, <em> e <strong> para quebras de linha e destaques. As outras formatações não são necessárias.'));
  const data=state.content.text[state.lang];
  const priority=Object.keys(textNames).filter(key=>key in data);
  const keys=[...priority,...Object.keys(data).filter(key=>!priority.includes(key))];
  main.append(panel('Conteúdo em '+langs[state.lang],el('div',{class:'text-grid'},keys.map(key=>draftField(textNames[key]||key,data,key,{multiline:true,help:key})))));
}
function deleteRecord(array,index,label) {if(confirm('Remover '+label+' do portfólio? A exclusão será publicada ao salvar.')){array.splice(index,1);markDirty();renderPage();}}
function reorder(array,index,direction) {const target=index+direction;if(target<0||target>=array.length)return;[array[index],array[target]]=[array[target],array[index]];markDirty();renderPage();}
function record(title,meta,description,actions,hidden=false) {return el('article',{class:'record'+(hidden?' hidden-record':'')},el('div',{},el('span',{class:'record-meta'},meta),el('h3',{},title),el('p',{},description)),el('div',{class:'record-actions'},actions));}
function renderJobs(main) {
  const jobs=state.content.jobs;
  main.append(pageHeader('Experiências','Crie, revise e organize sua trajetória profissional nos dois idiomas.',button('+ Adicionar experiência',()=>editJob(-1))));
  main.append(el('div',{class:'notice',style:'margin-bottom:20px'},'Ao atualizar sua trajetória, revise também os currículos em PDF. Os arquivos de download são substituídos em Foto e currículos.'));
  const list=el('div',{class:'card-list'});
  jobs.forEach((job,i)=>list.append(record(localized(job.company),localized(job.date),localized(job.title),[button('Editar',()=>editJob(i),'secondary small'),button('↑',()=>reorder(jobs,i,-1),'secondary small',{'aria-label':'Mover experiência para cima',disabled:i===0}),button('↓',()=>reorder(jobs,i,1),'secondary small',{'aria-label':'Mover experiência para baixo',disabled:i===jobs.length-1}),button('Excluir',()=>deleteRecord(jobs,i,'esta experiência'),'danger small')])));
  main.append(jobs.length?list:el('div',{class:'empty'},'Nenhuma experiência cadastrada. Adicione a primeira.'));
}
function editJob(index) {
  const job=index>=0?copy(state.content.jobs[index]):{company:{pt:'',en:''},date:{pt:'',en:''},title:{pt:'',en:''},description:{pt:'',en:''},extra:{pt:'',en:''},tags:[]};
  if(typeof job.company==='string')job.company={pt:job.company,en:job.company};job.extra??={pt:'',en:''};
  const nodes=[bilingualFields(job,[{key:'company',label:'Empresa'},{key:'date',label:'Período',help:'Ex.: OUT 2026 - ATUAL / OCT 2026 - PRESENT'},{key:'title',label:'Cargo'},{key:'description',label:'Descrição',multiline:true},{key:'extra',label:'Informações adicionais',multiline:true}]),field('Tecnologias · separadas por vírgula',job.tags.join(', '),v=>job.tags=listValue(v))];
  beginEditor(index>=0?'Editar experiência':'Nova experiência',nodes,()=>{if(!job.company.pt.trim()||!job.company.en.trim()||!job.title.pt.trim()||!job.title.en.trim())throw Error('Preencha empresa e cargo nos dois idiomas.');if(index<0)state.content.jobs.push(job);else state.content.jobs[index]=job;});
}
function renderProjects(main) {
  main.append(pageHeader('Projetos','Mantenha os estudos de caso e a documentação dos seus projetos no portfólio.',button('+ Estudo de caso',()=>editCase(-1))));
  main.append(el('div',{class:'section-title'},el('div',{},el('h3',{},'Projetos de IA e automação'),el('p',{},'Estudos de caso com contexto, contribuição, solução e resultado.'))));
  const list=el('div',{class:'card-list'});const cases=state.content.projects;
  cases.forEach((p,i)=>list.append(record(localized(p.title),'ESTUDO DE CASO / '+p.number,localized(p.description),[button('Editar',()=>editCase(i),'secondary small'),button('↑',()=>reorder(cases,i,-1),'secondary small',{'aria-label':'Mover projeto para cima',disabled:i===0}),button('↓',()=>reorder(cases,i,1),'secondary small',{'aria-label':'Mover projeto para baixo',disabled:i===cases.length-1}),button('Excluir',()=>deleteRecord(cases,i,'este projeto'),'danger small')])));
  main.append(cases.length?list:el('div',{class:'empty'},'Nenhum estudo de caso cadastrado.'));
  main.append(el('div',{class:'section-title'},el('div',{},el('h3',{},'Projetos no GitHub'),el('p',{},'Edite ou oculte a versão exibida no site. A issue original continua no GitHub.')),button('+ Documentação',()=>editIssue(null),'secondary')));
  const issues=el('div',{class:'card-list'});
  const all=[...state.issues,...state.content.customIssues];
  all.forEach(original=>{
    const custom=state.content.customIssues.some(p=>p.number===original.number);
    const over=state.content.issueOverrides[String(original.number)];
    const local=over?.translations?.[state.lang]||original.translations?.[state.lang]||original;
    const hidden=state.content.hiddenIssues.includes(original.number);
    const actions=[button('Editar',()=>editIssue(original),'secondary small')];
    if(custom)actions.push(button('Excluir',()=>{const idx=state.content.customIssues.findIndex(x=>x.number===original.number);deleteRecord(state.content.customIssues,idx,'esta documentação');},'danger small'));
    else actions.push(button(hidden?'Restaurar no site':'Ocultar do site',()=>{state.content.hiddenIssues=hidden?state.content.hiddenIssues.filter(n=>n!==original.number):[...state.content.hiddenIssues,original.number];markDirty();renderPage();},hidden?'secondary small':'danger small'));
    issues.append(record(local.title||'Projeto #'+original.number,(custom?'DOCUMENTAÇÃO AUTORAL':'GITHUB / #'+original.number)+(hidden?' · OCULTO':''),local.summary||'',actions,hidden));
  });
  main.append(all.length?issues:el('div',{class:'empty'},'As issues sincronizadas aparecerão aqui. Você também pode criar uma documentação diretamente no painel.'));
}
function editCase(index) {
  const p=index>=0?copy(state.content.projects[index]):{id:'project-'+Date.now(),number:String(state.content.projects.length+1).padStart(2,'0'),tags:[],title:{pt:'',en:''},description:{pt:'',en:''},flow:{pt:[],en:[]},details:{pt:{context:'',role:'',solution:'',result:''},en:{context:'',role:'',solution:'',result:''}}};
  const nodes=[el('div',{class:'form-grid'},field('Identificador',p.id,v=>p.id=v,{help:'Use letras, números e hífens.'}),field('Número exibido',p.number,v=>p.number=v)),bilingualFields(p,[{key:'title',label:'Título'},{key:'description',label:'Resumo',multiline:true}])];
  nodes.push(el('div',{class:'bilingual'},Object.entries(langs).map(([lang,label])=>el('div',{},el('p',{class:'lang-heading'},label),field('Etapas do fluxo · uma por linha',p.flow[lang].join('\n'),v=>p.flow[lang]=linesValue(v),{multiline:true}),['context','role','solution','result'].map((key,i)=>field(['O problema','Minha contribuição','A solução','Resultado'][i],p.details[lang][key],v=>p.details[lang][key]=v,{multiline:true}))))));
  nodes.push(field('Tecnologias · separadas por vírgula',p.tags.join(', '),v=>p.tags=listValue(v)));
  beginEditor(index>=0?'Editar estudo de caso':'Novo estudo de caso',nodes,()=>{if(!p.title.pt.trim()||!p.title.en.trim()||!p.id.trim())throw Error('Preencha identificador e título nos dois idiomas.');if(state.content.projects.some((x,i)=>i!==index&&x.id===p.id))throw Error('Este identificador já existe. Use outro.');if(index<0)state.content.projects.push(p);else state.content.projects[index]=p;});
}
function htmlToText(markup) {const doc=new DOMParser().parseFromString(markup||'','text/html');doc.querySelectorAll('br').forEach(n=>n.replaceWith('\n'));doc.querySelectorAll('p,h1,h2,h3,h4,li,pre').forEach(n=>n.append('\n\n'));return doc.body.textContent.replace(/\n{3,}/g,'\n\n').trim();}
function editIssue(original) {
  const isNew=!original;
  const existing=original&&state.content.issueOverrides[String(original.number)];
  const custom=original&&state.content.customIssues.some(p=>p.number===original.number);
  const number=original?.number || Math.max(1000000,...state.content.customIssues.map(p=>p.number))+1;
  const edited={number,translations:{},labels:copy(original?.labels||[]),updatedAt:new Date().toISOString(),url:original?.url||''};
  for(const lang of ['pt','en']) {
    const data=existing?.translations?.[lang]||original?.translations?.[lang]||(lang==='pt'?original:null)||{};
    edited.translations[lang]={title:data.title||'',summary:data.summary||'',bodyText:data.bodyText??htmlToText(data.bodyHtml),images:copy(data.images||[])};
  }
  const nodes=[el('div',{class:'notice'},'A descrição completa é editada como texto. Separe os parágrafos com uma linha em branco. As imagens existentes serão preservadas.')];
  nodes.push(el('div',{class:'bilingual'},Object.entries(langs).map(([lang,label])=>{
    const d=edited.translations[lang];
    return el('div',{},el('p',{class:'lang-heading'},label),field('Título',d.title,v=>d.title=v),field('Resumo',d.summary,v=>d.summary=v,{multiline:true}),field('Descrição completa',d.bodyText,v=>d.bodyText=v,{multiline:true,attrs:{rows:'16'}}),field('Imagens · um caminho por linha',d.images.join('\n'),v=>d.images=linesValue(v),{multiline:true,help:'Preserve os caminhos de imagens existentes ou use imagens enviadas pelo painel.'}));
  })));
  nodes.push(field('Etiquetas · separadas por vírgula',edited.labels.join(', '),v=>edited.labels=listValue(v)));
  beginEditor(isNew?'Nova documentação':'Editar documentação',nodes,()=>{
    if(!edited.translations.pt.title.trim()||!edited.translations.en.title.trim())throw Error('Preencha o título nos dois idiomas.');
    if(isNew)state.content.customIssues.push(edited);
    else if(custom){const index=state.content.customIssues.findIndex(p=>p.number===number);state.content.customIssues[index]=edited;}
    else state.content.issueOverrides[String(number)]={translations:edited.translations,labels:edited.labels,updatedAt:edited.updatedAt};
  });
}
function renderSkills(main) {
  const skills=state.content.skills;
  main.append(pageHeader('Competências','Organize as categorias e as tecnologias que aparecem no portfólio.',button('+ Categoria',()=>editSkill(-1))));
  const list=el('div',{class:'card-list'});
  skills.forEach((s,i)=>list.append(record(localized(s.title),'CATEGORIA / '+String(i+1).padStart(2,'0'),s.items.join(' · '),[button('Editar',()=>editSkill(i),'secondary small'),button('↑',()=>reorder(skills,i,-1),'secondary small',{'aria-label':'Mover categoria para cima',disabled:i===0}),button('Excluir',()=>deleteRecord(skills,i,'esta categoria'),'danger small')])));
  main.append(skills.length?list:el('div',{class:'empty'},'Nenhuma categoria cadastrada.'));
}
function editSkill(index) {
  const s=index>=0?copy(state.content.skills[index]):{title:{pt:'',en:''},items:[]};
  beginEditor(index>=0?'Editar competências':'Nova categoria',[bilingualFields(s,[{key:'title',label:'Nome da categoria'}]),field('Tecnologias · uma por linha',s.items.join('\n'),v=>s.items=linesValue(v),{multiline:true})],()=>{if(!s.title.pt.trim()||!s.title.en.trim())throw Error('Preencha o título nos dois idiomas.');if(index<0)state.content.skills.push(s);else state.content.skills[index]=s;});
}
async function fileMime(file) {
  const bytes=new Uint8Array(await file.slice(0,16).arrayBuffer());
  const matches=(offset,signature)=>signature.every((value,i)=>bytes[offset+i]===value);
  if(matches(0,[0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a]))return 'image/png';
  if(matches(0,[0xff,0xd8,0xff]))return 'image/jpeg';
  if(matches(0,[0x52,0x49,0x46,0x46])&&matches(8,[0x57,0x45,0x42,0x50]))return 'image/webp';
  if(matches(0,[0x25,0x50,0x44,0x46,0x2d]))return 'application/pdf';
  return '';
}
async function upload(file,kind,lang) {
  if(!file)return;
  const allowed=kind==='photo'?['image/png','image/jpeg','image/webp']:['application/pdf'];
  if(file.size>(kind==='photo'?5:15)*1024*1024){notify(kind==='photo'?'A imagem deve ter no máximo 5 MB.':'O PDF deve ter no máximo 15 MB.',true);return;}
  let mime;
  try{mime=await fileMime(file);}catch{notify('Não foi possível ler o arquivo. Selecione-o novamente.',true);return;}
  if(!allowed.includes(mime)){notify(kind==='photo'?'O arquivo precisa ser uma imagem PNG, JPEG ou WebP válida.':'O arquivo precisa ser um PDF válido.',true);return;}
  const inputs=[...document.querySelectorAll('.file-input')];inputs.forEach(i=>i.disabled=true);
  try {const data=await api('upload?kind='+kind+(lang?'&lang='+lang:''),{method:'POST',headers:{'Content-Type':mime},body:file});if(kind==='photo')state.content.profile.photo=data.url;else state.content.profile.resume[lang]=data.url;markDirty();renderPage();notify('Arquivo enviado. Publique as alterações para usá-lo no site.');}
  catch(error){notify(error.message,true);inputs.forEach(i=>i.disabled=false);}
}
function renderFiles(main) {
  const p=state.content.profile;
  main.append(pageHeader('Foto e currículos','Substitua sua foto e os PDFs de download em português e inglês.'));
  const image=el('img',{src:siteUrl(p.photo),alt:p.photoAlt||'Foto atual',class:'photo-preview'});
  const photoInput=el('input',{type:'file',class:'file-input',accept:'image/png,image/jpeg,image/webp','aria-label':'Enviar nova foto',onChange:e=>upload(e.target.files[0],'photo')});
  main.append(panel('Foto de perfil',image,el('div',{class:'file-row'},el('div',{},el('strong',{},'Enviar nova foto'),el('p',{},'PNG, JPEG ou WebP · até 5 MB')),photoInput),el('p',{class:'help'},'A foto só muda no site depois de publicar.')));
  const pdfs=panel('Currículos para download');
  for(const [lang,label] of Object.entries(langs))pdfs.append(el('div',{class:'file-row'},el('div',{},el('strong',{},'Currículo · '+label),el('p',{},el('a',{href:siteUrl(p.resume[lang]),target:'_blank',rel:'noopener'},'Abrir arquivo atual ↗')),el('p',{},'PDF · até 15 MB')),el('input',{type:'file',class:'file-input',accept:'application/pdf','aria-label':'Enviar currículo em '+label,onChange:e=>upload(e.target.files[0],'resume',lang)})));
  main.append(pdfs,el('div',{class:'notice'},'Os currículos são arquivos próprios. Ao mudar sua experiência, revise também os PDFs e envie as versões atualizadas.'));
}
function renderTheme(main) {
  const theme=state.content.theme;
  main.append(pageHeader('Cores e temas','Ajuste a identidade visual dos modos claro e escuro. As cores do painel permanecem independentes.'));
  main.append(panel('Tema inicial',field('Tema para novos visitantes',theme.default,v=>{theme.default=v;markDirty();},{select:[['light','Claro'],['dark','Escuro']]})));
  for(const [mode,label] of [['light','Modo claro'],['dark','Modo escuro']]) {
    const palette=theme[mode];
    const preview=el('div',{class:'theme-preview'},el('p',{},'Thalyson Emanuel'),el('span',{},'Ver projetos'));
    const update=()=>{preview.style.background=palette.background||palette['--bg']||'#fff';preview.style.color=palette.text||palette['--text']||'#17263d';const badge=preview.querySelector('span');badge.style.background=palette.primary||palette.accent||'#1759d5';badge.style.color=palette['on-primary']||'#fff';};update();
    const grid=el('div',{class:'color-grid'});
    Object.entries(palette).forEach(([key,value])=>{
      const picker=el('input',{type:'color',value:value.slice(0,7),'aria-label':label+' '+key});const input=el('input',{type:'text',value,pattern:'#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?',maxlength:'9','aria-label':'Código '+label+' '+key});
      const sync=v=>{if(/^#[0-9a-f]{6}([0-9a-f]{2})?$/i.test(v)){palette[key]=v;picker.value=v.slice(0,7);input.value=v;markDirty();update();}};
      picker.addEventListener('input',()=>sync(picker.value+(palette[key].length===9?palette[key].slice(7):'')));input.addEventListener('input',()=>sync(input.value));
      grid.append(el('div',{class:'field'},el('span',{class:'field-label'},key.replace(/^--/,'')),el('div',{class:'color-control'},picker,input)));
    });
    main.append(panel(label,preview,grid));
  }
}
function renderSecurity(main) {
  main.append(pageHeader('Acesso e senha','Gerencie sua senha e encerre a sessão quando terminar.'));
  main.append(panel('Administrador',el('p',{},state.session.email),el('p',{class:'help'},'Este e-mail identifica o administrador. O e-mail público é editado em Perfil e contato.')));
  const data={currentPassword:'',password:'',confirm:''};const form=el('form',{class:'stack setting-form'});
  form.append(field('Senha atual','',v=>data.currentPassword=v,{type:'password',attrs:{required:'',autocomplete:'current-password'}}),field('Nova senha','',v=>data.password=v,{type:'password',attrs:{required:'',autocomplete:'new-password',minlength:'12'},help:'Pelo menos 12 caracteres.'}),field('Confirme a nova senha','',v=>data.confirm=v,{type:'password',attrs:{required:'',autocomplete:'new-password',minlength:'12'}}));
  const error=el('p',{class:'error',role:'alert'});const submit=el('button',{class:'button',type:'submit'},'Atualizar senha');form.append(error,submit);
  form.addEventListener('submit',async event=>{event.preventDefault();error.textContent='';if(data.password!==data.confirm){error.textContent='As novas senhas não coincidem.';return;}if(state.dirty&&!confirm('A troca de senha encerra a sessão. Seu rascunho ainda não foi publicado. Deseja continuar?'))return;submit.disabled=true;try{await jsonRequest('password',{currentPassword:data.currentPassword,password:data.password});state.dirty=false;state.content=null;state.session=await api('session');renderAuth('Senha atualizada. Entre com sua nova senha.');}catch(e){error.textContent=e.message;submit.disabled=false;}});
  main.append(panel('Trocar senha',form));
  main.append(panel('Sessão atual',button('Sair do painel',async()=>{if(state.dirty&&!confirm('Sair e descartar as alterações não publicadas?'))return;try{await jsonRequest('logout',{});state.dirty=false;state.content=null;state.session=await api('session');renderAuth();}catch(e){notify(e.message,true);}},'secondary')));
}
function renderAdvanced(main) {
  main.append(pageHeader('Conteúdo completo','Exporte uma cópia do conteúdo ou ajuste campos adicionais no formato JSON.'));
  const textarea=el('textarea',{class:'code-input',spellcheck:'false','aria-label':'Conteúdo completo em JSON'});textarea.value=JSON.stringify(state.content,null,2);
  const error=el('p',{class:'error',role:'alert'});
  const exportData=()=>{const blob=new Blob([JSON.stringify(state.content,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=el('a',{href:url,download:'tedsp-portfolio-conteudo.json'});a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  main.append(el('div',{class:'notice',style:'margin-bottom:20px'},'A cópia contém o conteúdo público do site. Senhas e sessões não fazem parte deste arquivo.'));
  main.append(panel('JSON do portfólio',el('div',{class:'toolbar'},button('Exportar conteúdo',exportData,'secondary'),button('Aplicar JSON ao rascunho',()=>{try{const value=JSON.parse(textarea.value);if(!value.text?.pt||!value.text?.en||!Array.isArray(value.jobs)||!Array.isArray(value.projects)||!Array.isArray(value.skills)||!Array.isArray(value.hiddenIssues)||!Array.isArray(value.customIssues)||!value.issueOverrides||!value.profile?.resume||!Array.isArray(value.profile.metrics)||!value.theme?.light||!value.theme?.dark)throw Error('A estrutura precisa conter os campos originais do portfólio.');state.content=value;markDirty();error.textContent='';notify('JSON aplicado ao rascunho. Revise antes de publicar.');}catch(e){error.textContent=e.message;}},'secondary')),el('div',{class:'field'},textarea),error));
}

start();
