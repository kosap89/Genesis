'use strict';
(() => {
  const $ = (id) => document.getElementById(id);
  let state = null;
  let venture = '';
  let selectedTask = null;
  let refreshBusy = false;
  let detailBusy = false;
  let settingsInitialized = false;
  let credentialsInitialized = false;
  let agentSignature = '';
  const titles = {overview:['Command center','Set the direction. Review the work. Keep control.'],operations:['Operations','Follow objectives from instruction to evidence.'],knowledge:['Company knowledge','Preserve context and develop the next opportunity.'],artifacts:['Artifacts','The tangible output of your company’s work.'],settings:['Agents & controls','Configure capabilities, models, and the limits of execution.'],audit:['Activity log','A persistent record of actions and decisions.']};
  const el = (tag, text, cls) => { const n=document.createElement(tag); if(text!==undefined && text!==null)n.textContent=String(text); if(cls)n.className=cls; return n; };
  const arr = (x) => Array.isArray(x) ? x : [];
  const stringify = (x) => typeof x==='string' ? x : JSON.stringify(x,null,2) || '';
  const date = (x) => x ? new Date(x).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '';
  const money = (x) => new Intl.NumberFormat(undefined,{style:'currency',currency:'USD'}).format(Number(x)||0);
  const scoped = (items) => arr(items).filter(x=>!venture || x.venture_id===venture);
  const empty = (host,text) => host.append(el('div',text,'empty'));
  const status = (value) => el('span', String(value||'unknown').replaceAll('_',' '),'status '+String(value||'').replace(/[^a-z_]/g,''));
  const button = (text, action, cls='secondary') => {const b=el('button',text,cls);b.type='button';b.addEventListener('click',()=>run(b,action));return b;};
  function feedback(message,error=false){const n=$('feedback');n.textContent=message;n.className=error?'error':'';n.hidden=false;}
  async function api(path,body){const options={headers:{Accept:'application/json'}};if(body!==undefined){options.method='POST';options.headers['Content-Type']='application/json';options.headers['X-Genesis-CSRF']=state?.csrf_token||'';options.body=JSON.stringify(body);}const response=await fetch(path,options);let data;try{data=await response.json();}catch{throw new Error('The server returned an unreadable response.');}if(!response.ok)throw new Error(typeof data.error==='string'?data.error:data.error?.message||data.message||`Request failed (${response.status}).`);return data;}
  async function run(b, action){if(b)b.disabled=true;try{await action();}catch(e){feedback(e.message,true);}finally{if(b)b.disabled=false;}}
  async function mutate(path,body,message){await api(path,body);if(message)feedback(message);await refresh();}
  function showView(view){if(!titles[view])return;document.querySelectorAll('.view').forEach(n=>n.hidden=n.id!=='view-'+view);document.querySelectorAll('[data-view]').forEach(n=>{n.classList.toggle('active',n.dataset.view===view);if(n.dataset.view===view)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current');});$('view-title').textContent=titles[view][0];$('view-description').textContent=titles[view][1];}
  document.querySelectorAll('[data-view]').forEach(n=>n.addEventListener('click',()=>showView(n.dataset.view)));
  document.querySelectorAll('[data-go]').forEach(n=>n.addEventListener('click',()=>showView(n.dataset.go)));
  document.querySelectorAll('[data-close]').forEach(n=>n.addEventListener('click',()=>$(n.dataset.close).close()));
  $('new-venture').addEventListener('click',()=>$('venture-dialog').showModal());
  $('venture-select').addEventListener('change',()=>{venture=$('venture-select').value;render();});
  $('task-filter').addEventListener('change',()=>renderTasks($('all-tasks'),scoped(state?.tasks)));
  function renderTasks(host,tasks,limit){host.replaceChildren();let list=[...tasks].sort((a,b)=>String(b.created_at).localeCompare(String(a.created_at)));if(host.id==='all-tasks'&&$('task-filter').value)list=list.filter(t=>t.status===$('task-filter').value);if(limit)list=list.slice(0,limit);if(!list.length)return empty(host,'No objectives here yet. Create an objective to begin real execution.');list.forEach(t=>{const row=el('article',null,'record');row.dataset.taskId=t.id;const top=el('div',null,'record-top');top.append(button(t.title||t.objective||t.id,()=>openTask(t.id),'record-title'),status(t.status));row.append(top,el('div',[t.role,t.provider,t.model,date(t.updated_at||t.created_at)].filter(Boolean).join(' · '),'record-meta'));if(t.error)row.append(el('p',stringify(t.error),'danger'));host.append(row);});}
  function renderApprovals(host){host.replaceChildren();const tasks=new Map(arr(state.tasks).map(t=>[t.id,t]));const list=arr(state.approvals).filter(a=>['pending','waiting','requested'].includes(a.status||'pending')&&(!venture||tasks.get(a.task_id)?.venture_id===venture));if(!list.length)return empty(host,'No decisions waiting. Actions requiring approval will appear here.');for(const a of list){const row=el('article',null,'record');row.dataset.approvalId=a.id;const top=el('div',null,'record-top');top.append(el('h3',a.action||'Requested action'),status(a.status||'pending'));row.append(top,el('p',tasks.get(a.task_id)?.title||a.task_id||''),el('pre',stringify(a.details)));const controls=el('div',null,'record-actions');for(const decision of ['approved','denied'])controls.append(button(decision==='approved'?'Approve action':'Deny',()=>mutate('/api/approvals/'+encodeURIComponent(a.id),{decision},decision==='approved'?'Action approved.':'Action denied.'),decision==='approved'?'primary':'secondary danger'));controls.append(button('Inspect objective',()=>openTask(a.task_id),'text-button'));row.append(controls);host.append(row);}}
  function renderKnowledge(host,items,kind){host.replaceChildren();if(!items.length)return empty(host,kind==='memory'?'No saved company memory yet.':'No opportunities recorded yet.');for(const item of [...items].reverse()){const row=el('article',null,'record');const top=el('div',null,'record-top');top.append(el('h3',item.title));if(item.status)top.append(status(item.status));row.append(top,el('p',item.content||item.summary),el('div',date(item.created_at),'record-meta'));host.append(row);}}
  function renderArtifacts(host,items){host.replaceChildren();if(!items.length)return empty(host,'No artifacts yet. Files will appear after an execution produces them.');for(const a of [...items].reverse()){const row=el('article',null,'record');const link=el('a',a.name||a.path||a.id,'artifact-link');link.href='/api/artifacts/'+encodeURIComponent(a.id);link.target='_blank';link.rel='noopener';row.append(link,el('div',[a.task_id,date(a.created_at)].filter(Boolean).join(' · '),'record-meta'));host.append(row);}}
  function providers(){if(Array.isArray(state.providers))return state.providers.map(p=>typeof p==='string'?{id:p,name:p}:p);return Object.entries(state.providers||{}).map(([id,p])=>typeof p==='object'?{id,...p}:{id,name:id,configured:Boolean(p)});}
  function providerId(p){return p.id||p.provider||p.name;}
  function providerReady(p){return Boolean(p.configured??p.available??p.ready??p.enabled);}
  function renderProviders(){const host=$('provider-list');host.replaceChildren();const list=providers();if(!list.length)empty(host,'No model provider is configured. Add a session key below.');for(const p of list){const row=el('div',null,'record');const top=el('div',null,'record-top');top.append(el('h3',p.name||providerId(p)),status(providerReady(p)?'configured':'not_configured'));row.append(top);const env=p.env_var||p.env_key||p.key_env||({openai:'OPENAI_API_KEY',anthropic:'ANTHROPIC_API_KEY',gemini:'GEMINI_API_KEY',google:'GEMINI_API_KEY'}[providerId(p)]);if(!providerReady(p))row.append(el('p',env?`Add a session key below, or set ${env} before launching Genesis.`:p.setup||'Add a session key below.'));if(p.base_url)row.append(el('div',p.base_url,'record-meta'));host.append(row);}const anyReady=list.some(providerReady);$('setup-notice').hidden=anyReady;if(!anyReady)$('setup-notice').textContent='Model setup required. Open Agents & controls to add a provider key for this session. Objectives cannot execute model work until a provider is available.';if(!credentialsInitialized){$('credentials-configure-agents').checked=!anyReady;credentialsInitialized=true;}}
  function renderAgents(){
    const agents=arr(state.agents);
    const signature=JSON.stringify(agents)+JSON.stringify(providers().map(p=>[providerId(p),p.models]));
    if(signature===agentSignature)return;
    const host=$('agent-list');
    if(host.contains(document.activeElement))return;
    agentSignature=signature;host.replaceChildren();
    const role=$('objective-role');const prior=role.value;role.replaceChildren();
    for(const a of agents){
      const opt=el('option',a.name||a.role);opt.value=a.role;role.append(opt);
      const form=el('form',null,'item-card agent-form');form.dataset.role=a.role;
      form.append(el('h3',a.name||a.role),el('p',a.description||'Configured agent role.','muted'));
      const pl=el('label','Provider');const select=el('select');select.name='provider';
      const ids=new Set(providers().map(providerId));if(a.provider)ids.add(a.provider);
      for(const id of ids){const o=el('option',id);o.value=id;select.append(o);}
      if(!ids.size){const o=el('option','No providers available');o.value='';select.append(o);}
      select.value=a.provider||select.value;pl.append(select);
      const ml=el('label','Model identifier');const input=el('input');input.name='model';input.value=a.model||'';input.required=true;input.placeholder='Exact provider model ID';ml.append(input);
      form.append(pl,ml);
      for(const [field,label] of [['input_cost_per_million','Input rate estimate (USD / million tokens)'],['output_cost_per_million','Output rate estimate (USD / million tokens)']]){
        const labelNode=el('label',label);const rate=el('input');rate.name=field;rate.type='number';rate.min='0.001';rate.max='100000';rate.step='0.001';rate.required=true;rate.value=a[field]??(field.startsWith('input')?10:30);labelNode.append(rate);form.append(labelNode);
      }
      const fl=el('label','Fallback routes (optional JSON, maximum two)');const fallbacks=el('textarea');fallbacks.name='fallbacks';fallbacks.rows=3;fallbacks.value=JSON.stringify(a.fallbacks||[],null,2);fallbacks.placeholder='[{"provider":"anthropic","model":"model-id"}]';fl.append(fallbacks);form.append(fl);
      form.append(el('p','Rates are configured estimates, not provider invoices or a guaranteed spending cap. Fallback requests may also incur charges.','muted'));
      const save=el('button','Save configuration','secondary');save.type='submit';form.append(save);
      form.addEventListener('submit',e=>{e.preventDefault();run(save,async()=>{
        let routes;try{routes=JSON.parse(fallbacks.value.trim()||'[]');}catch{throw new Error('Fallback routes must be valid JSON.');}
        if(!Array.isArray(routes)||routes.length>2||routes.some(r=>!r||typeof r!=='object'||Array.isArray(r)||Object.keys(r).sort().join(',')!=='model,provider'||!['openai','anthropic','gemini'].includes(r.provider)||typeof r.model!=='string'||!r.model.trim()))throw new Error('Use at most two fallback objects, each with a supported provider and a model identifier.');
        await mutate('/api/agents/'+encodeURIComponent(a.role),{provider:select.value,model:input.value.trim(),input_cost_per_million:Number(form.elements.input_cost_per_million.value),output_cost_per_million:Number(form.elements.output_cost_per_million.value),fallbacks:routes},'Agent configuration saved.');
        agentSignature='';form.querySelector(':focus')?.blur();renderAgents();
      });});host.append(form);
    }
    if(agents.some(a=>a.role===prior))role.value=prior;
    if(!agents.length){const o=el('option','Default agent');o.value='coo';role.append(o);empty(host,'Agent roles are not available yet.');}
  }
  function eventDetails(event){const {id,action,type,event:kind,created_at,timestamp,...details}=event;return Object.keys(details).length?details:null;}
  function renderAudit(){const host=$('audit-list');host.replaceChildren();let list=arr(state.audit);if(venture){const ids=new Set(scoped(state.tasks).map(t=>t.id));list=list.filter(a=>a.venture_id===venture||ids.has(a.task_id)||ids.has(a.entity_id));}if(!list.length)return empty(host,'No recorded activity yet.');for(const event of [...list].sort((a,b)=>String(b.created_at||b.timestamp).localeCompare(String(a.created_at||a.timestamp))).slice(0,150)){const row=el('article',null,'record');const top=el('div',null,'record-top');top.append(el('h3',event.action||event.type||event.event||'System event'),el('span',date(event.created_at||event.timestamp),'muted'));row.append(top);const details=eventDetails(event);if(details)row.append(el('pre',stringify(details)));host.append(row);}}
  function render(){if(!state)return;const ventures=arr(state.ventures);const options=JSON.stringify(ventures.map(v=>[v.id,v.name]));if($('venture-select').dataset.signature!==options){$('venture-select').replaceChildren(el('option','All ventures'));$('venture-select').firstChild.value='';for(const v of ventures){const o=el('option',v.name);o.value=v.id;$('venture-select').append(o);}$('venture-select').dataset.signature=options;}if(venture&&!ventures.some(v=>v.id===venture))venture='';$('venture-select').value=venture;$('workspace-name').textContent=ventures.find(v=>v.id===venture)?.name||'All ventures';const tasks=scoped(state.tasks);const pending=arr(state.approvals).filter(a=>['pending','waiting','requested'].includes(a.status||'pending')&&(!venture||tasks.some(t=>t.id===a.task_id)));$('task-count').textContent=tasks.length||'';$('metric-active').textContent=tasks.filter(t=>['queued','running','waiting_approval','waiting_children'].includes(t.status)).length;$('metric-completed').textContent=tasks.filter(t=>t.status==='completed').length;$('metric-approvals').textContent=pending.length;const s=state.settings||{};$('metric-budget').textContent=money(Math.max(0,Number(s.budget_usd||0)-Number(s.spent_usd||0)-Number(s.reserved_usd||0)));$('metric-spent').textContent=money(s.spent_usd)+' spent · '+money(s.reserved_usd)+' reserved';$('usage-detail').textContent=`Spent ${money(s.spent_usd)} · Reserved ${money(s.reserved_usd)} · Budget ${money(s.budget_usd)}`;renderTasks($('recent-tasks'),tasks,5);renderTasks($('all-tasks'),tasks);renderApprovals($('approval-list'));renderApprovals($('all-approvals'));const vl=$('venture-list');vl.replaceChildren();const vs=ventures.filter(v=>!venture||v.id===venture);if(!vs.length)empty(vl,'No ventures yet. Create a venture to organize objectives and knowledge.');for(const v of vs){const card=el('article',null,'item-card');card.append(el('h3',v.name),el('p',v.description,'muted'),el('div',`${arr(state.tasks).filter(t=>t.venture_id===v.id).length} objectives`,'record-meta'));if(v.status)card.append(status(v.status));vl.append(card);}renderKnowledge($('memory-list'),scoped(state.memories),'memory');renderKnowledge($('opportunity-list'),scoped(state.opportunities),'opportunity');const ids=new Set(tasks.map(t=>t.id));renderArtifacts($('artifact-list'),arr(state.artifacts).filter(a=>!venture||a.venture_id===venture||ids.has(a.task_id)));renderProviders();renderAgents();renderAudit();if(!settingsInitialized){$('budget-usd').value=s.budget_usd??0;$('max-steps').value=s.max_steps??10;$('allow-network').checked=Boolean(s.allow_network);$('allow-terminal').checked=Boolean(s.allow_terminal);settingsInitialized=true;}}
  async function refresh(){if(refreshBusy)return;refreshBusy=true;try{state=await api('/api/state');render();$('connection').textContent='Connected to local server';$('connection-dot').classList.add('online');$('updated').textContent='Updated '+new Date().toLocaleTimeString(undefined,{hour:'2-digit',minute:'2-digit'});}catch(e){$('connection').textContent='Server unavailable';$('connection-dot').classList.remove('online');feedback(e.message,true);}finally{refreshBusy=false;}}
  $('objective-form').addEventListener('submit',e=>{e.preventDefault();const objective=$('objective').value.trim();if(!objective)return;run($('submit-objective'),async()=>{const data=await api('/api/tasks',{objective,role:$('objective-role').value,...(venture?{venture_id:venture}:{})});$('objective').value='';feedback('Objective created. Execution status will appear below.');await refresh();const task=data.task||data;if(task.id)await openTask(task.id);});});
  $('venture-form').addEventListener('submit',e=>{e.preventDefault();const f=e.currentTarget;run(f.querySelector('[type=submit]'),async()=>{const fd=new FormData(f);await mutate('/api/ventures',{name:fd.get('name').trim(),description:fd.get('description').trim()},'Venture created.');f.reset();$('venture-dialog').close();});});
  for(const kind of ['memory','opportunity'])$(kind+'-form').addEventListener('submit',e=>{e.preventDefault();const f=e.currentTarget;run(f.querySelector('[type=submit]'),async()=>{const fd=new FormData(f);const body=Object.fromEntries(fd);if(venture)body.venture_id=venture;await mutate(kind==='memory'?'/api/memories':'/api/opportunities',body,kind==='memory'?'Company memory saved.':'Opportunity added.');f.reset();});});
  $('settings-form').addEventListener('submit',e=>{e.preventDefault();run(e.currentTarget.querySelector('[type=submit]'),async()=>{await mutate('/api/settings',{budget_usd:Number($('budget-usd').value),max_steps:Number($('max-steps').value),allow_network:$('allow-network').checked,allow_terminal:$('allow-terminal').checked},'Execution controls saved.');});});
  $('credentials-form').addEventListener('submit',e=>{
    e.preventDefault();
    const provider=$('credentials-provider').value;
    const key=$('credentials-key').value;
    const configure_agents=$('credentials-configure-agents').checked;
    $('credentials-key').value='';
    run(e.currentTarget.querySelector('[type=submit]'),async()=>{
      try{
        await api('/api/credentials',{provider,api_key:key,configure_agents});
        feedback(configure_agents?'Session key saved and agent default routes configured. Existing objectives keep their route until explicitly resumed with agent settings.':'Session key saved. Review agent routes and resume blocked objectives when ready.');
        agentSignature='';await refresh();
      }finally{$('credentials-key').value='';}
    });
  });
  $('credentials-clear').addEventListener('click',e=>{
    $('credentials-key').value='';
    run(e.currentTarget,async()=>{
      try{
        const result=await api('/api/credentials',{provider:$('credentials-provider').value,api_key:'',configure_agents:false});
        feedback(result.configured?'Process override cleared. An inherited environment key remains configured.':'Process override cleared. This provider has no configured key.');
        await refresh();
      }finally{$('credentials-key').value='';}
    });
  });
  async function openTask(id){selectedTask=id;if(!$('task-dialog').open)$('task-dialog').showModal();$('detail-title').textContent='Objective details';$('task-detail').replaceChildren(el('p','Loading execution history…','muted'));await refreshDetail();}
  async function refreshDetail(){
    if(!selectedTask||!$('task-dialog').open||detailBusy)return;detailBusy=true;const id=selectedTask;
    try{
      const data=await api('/api/tasks/'+encodeURIComponent(id));if(id!==selectedTask)return;
      const t=data.task||{};const host=$('task-detail');host.replaceChildren();$('detail-title').textContent=t.title||'Objective details';
      const heading=el('div',null,'record-top');heading.append(status(t.status),el('span',[t.role,t.provider,t.model].filter(Boolean).join(' · '),'muted'));host.append(heading,el('p',t.objective||t.title||''));
      const controls=el('div',null,'record-actions');
      const bundle=el('a','Download task ZIP','secondary');bundle.href='/api/tasks/'+encodeURIComponent(id)+'/bundle';bundle.target='_blank';bundle.rel='noopener';controls.append(bundle);
      if(!['completed','cancelled','failed'].includes(t.status))controls.append(button('Cancel objective',()=>mutate('/api/tasks/'+encodeURIComponent(id)+'/cancel',{},'Objective cancelled.'),'secondary danger'));
      if(['interrupted','blocked_credentials','blocked_budget','paused_limit','failed'].includes(t.status)){
        controls.append(button('Resume objective',()=>mutate('/api/tasks/'+encodeURIComponent(id)+'/resume',{},'Resume requested.')));
        const agent=arr(state?.agents).find(a=>a.role===t.role);
        if(agent?.provider&&agent?.model){
          const reroute=button('Resume with agent settings',()=>mutate('/api/tasks/'+encodeURIComponent(id)+'/resume',{provider:agent.provider,model:agent.model},`Resume requested using ${agent.provider} / ${agent.model}.`));
          reroute.title=`Use the ${t.role} agent's configured route: ${agent.provider} / ${agent.model}`;
          controls.append(reroute);
        }
      }
      host.append(controls,el('div',`Created ${date(t.created_at)} · Updated ${date(t.updated_at)} · Step ${t.step||0} · Estimated cost ${money(t.cost_usd)}`,'record-meta'));
      if(t.error){const box=el('div',null,'detail-section');box.append(el('h3','Execution error'),el('pre',stringify(t.error),'danger'));host.append(box);}
      if(t.result){const box=el('div',null,'detail-section');box.append(el('h3','Result'),el('pre',stringify(t.result)));host.append(box);}
      const ms=el('div',null,'detail-section');ms.append(el('h3','Model messages & tool records'));
      if(!arr(data.messages).length)empty(ms,'No model messages recorded.');
      for(const m of arr(data.messages)){
        const msg=el('div',null,'message');msg.append(el('strong',[m.role||m.type||'Message',m.name].filter(Boolean).join(' · ')));
        if(m.content??m.message)msg.append(el('div',stringify(m.content??m.message)));
        if(arr(m.tool_calls).length){msg.append(el('strong','Requested tool calls'),el('pre',stringify(m.tool_calls)));}
        if(m.tool_call_id)msg.append(el('div','Tool call '+m.tool_call_id,'record-meta'));
        ms.append(msg);
      }
      host.append(ms);
      const es=el('div',null,'detail-section');es.append(el('h3','Execution timeline'));const tl=el('div',null,'timeline');
      if(!arr(data.events).length)empty(tl,'No execution events recorded.');
      for(const event of [...arr(data.events)].sort((a,b)=>String(a.created_at||a.timestamp).localeCompare(String(b.created_at||b.timestamp)))){
        const row=el('div',null,'record');row.append(el('h3',event.type||event.action||event.event||'Event'),el('span',date(event.created_at||event.timestamp),'record-meta'));
        const details=eventDetails(event);if(details)row.append(el('pre',stringify(details)));tl.append(row);
      }
      es.append(tl);host.append(es);
      const as=el('div',null,'detail-section');as.append(el('h3','Artifacts'));const files=el('div');renderArtifacts(files,arr(data.artifacts));as.append(files);host.append(as);
    }catch(e){feedback(e.message,true);}finally{detailBusy=false;}
  }
  $('task-dialog').addEventListener('close',()=>{selectedTask=null;});
  refresh();
  setInterval(()=>{if(!document.hidden){refresh();refreshDetail();}},3000);
})();
