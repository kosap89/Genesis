'use strict';
(() => {
  const $ = (id) => document.getElementById(id);
  let state = null;
  let venture = new URLSearchParams(location.search).get('venture') || '';
  let documentSignature = '';
  let selectedDocument = null;
  let selectedTask = null;
  let refreshBusy = false;
  let detailBusy = false;
  let settingsInitialized = false;
  let credentialsInitialized = false;
  let agentSignature = '';
  let teamSignature = '';
  let previewTimer;
  let previewVersion = 0;
  let objectiveRoute = '';
  let requestedMission = new URLSearchParams(location.search).get('mission') === '1';
  const projectLimitKeys=['max_concurrency','max_steps','max_output_tokens','max_delegation_depth','max_delegated_tasks'];
  let resumeAuthorization = {task:null,checked:false};
  const titles = {overview:['Command center','Set the direction. Review the work. Keep control.'],operations:['Operations','Follow objectives from instruction to evidence.'],knowledge:['Company knowledge','Preserve context and develop the next opportunity.'],artifacts:['Artifacts','The tangible output of your company’s work.'],settings:['Agents & controls','Configure capabilities, models, and the limits of execution.'],audit:['Activity log','A persistent record of actions and decisions.']};
  const el = (tag, text, cls) => { const n=document.createElement(tag); if(text!==undefined && text!==null)n.textContent=String(text); if(cls)n.className=cls; return n; };
  const arr = (x) => Array.isArray(x) ? x : [];
  const stringify = (x) => typeof x==='string' ? x : JSON.stringify(x,null,2) || '';
  const date = (x) => x ? new Date(x).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '';
  const money = (x) => new Intl.NumberFormat(undefined,{style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:6}).format(Number(x)||0);
  const scoped = (items) => arr(items).filter(x=>!venture || x.venture_id===venture);
  const empty = (host,text) => host.append(el('div',text,'empty'));
  const status = (value) => el('span', String(value||'unknown').replaceAll('_',' '),'status '+String(value||'').replace(/[^a-z_]/g,''));
  const button = (text, action, cls='secondary') => {const b=el('button',text,cls);b.type='button';b.addEventListener('click',()=>run(b,action));return b;};
  function feedback(message,error=false){const n=$('feedback');n.textContent=message;n.className=error?'error':'';n.hidden=false;}
  async function api(path,body){const options={headers:{Accept:'application/json'}};if(body!==undefined){options.method='POST';options.headers['Content-Type']='application/json';options.headers['X-Genesis-CSRF']=state?.csrf_token||'';options.body=JSON.stringify(body);}const response=await fetch(path,options);let data;try{data=await response.json();}catch{throw new Error('The server returned an unreadable response.');}if(!response.ok)throw new Error(typeof data.error==='string'?data.error:data.error?.message||data.message||`Request failed (${response.status}).`);return data;}
  async function run(b, action){if(b)b.disabled=true;try{await action();}catch(e){feedback(e.message,true);}finally{if(b)b.disabled=false;}}
  async function mutate(path,body,message){await api(path,body);if(message)feedback(message);await refresh();}
  function updateLocation(view){const url=new URL(location.href);if(venture)url.searchParams.set('venture',venture);else url.searchParams.delete('venture');if(view)url.searchParams.set('view',view);history.replaceState(null,'',url);}
  function showView(view){if(!titles[view])return;updateLocation(view);document.querySelectorAll('.view').forEach(n=>n.hidden=n.id!=='view-'+view);document.querySelectorAll('[data-view]').forEach(n=>{n.classList.toggle('active',n.dataset.view===view);if(n.dataset.view===view)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current');});$('view-title').textContent=titles[view][0];$('view-description').textContent=titles[view][1];}
  titles.finance=['Financial dashboard','Compare local budget accounting with delayed official OpenAI reports.'];
  titles.documents=['Venture documents','Read source references, revise working documents and preserve decisions.'];
  titles.team=['Agent Team','Build the selected project’s team and assign work to specific agents.'];
  document.querySelectorAll('[data-view]').forEach(n=>n.addEventListener('click',()=>showView(n.dataset.view)));
  document.querySelectorAll('[data-go]').forEach(n=>n.addEventListener('click',()=>showView(n.dataset.go)));
  document.querySelectorAll('[data-close]').forEach(n=>n.addEventListener('click',()=>$(n.dataset.close).close()));
  $('new-venture').addEventListener('click',()=>$('venture-dialog').showModal());
  $('venture-select').addEventListener('change',()=>{venture=$('venture-select').value;selectedDocument=null;$('document-editor').hidden=true;delete $('project-policy-form').dataset.dirty;delete $('project-limits-form').dataset.dirty;delete $('project-mission-form').dataset.dirty;documentSignature='';updateLocation();resetObjectiveAuthorization();render();schedulePreview();});
  $('task-filter').addEventListener('change',()=>renderTasks($('all-tasks'),scoped(state?.tasks)));
  function renderTasks(host,tasks,limit){host.replaceChildren();let list=[...tasks].sort((a,b)=>String(b.created_at).localeCompare(String(a.created_at)));if(host.id==='all-tasks'&&$('task-filter').value)list=list.filter(t=>t.status===$('task-filter').value);if(limit)list=list.slice(0,limit);if(!list.length)return empty(host,'No objectives here yet. Create an objective to begin real execution.');list.forEach(t=>{const row=el('article',null,'record');row.dataset.taskId=t.id;const top=el('div',null,'record-top');top.append(button(t.title||t.objective||t.id,()=>openTask(t.id),'record-title'),status(t.status));row.append(top,el('div',[agentAttribution(t),t.provider,t.model,date(t.updated_at||t.created_at)].filter(Boolean).join(' · '),'record-meta'));if(t.error)row.append(el('p',stringify(t.error),'danger'));host.append(row);});}
  function renderApprovals(host){host.replaceChildren();const tasks=new Map(arr(state.tasks).map(t=>[t.id,t]));const list=arr(state.approvals).filter(a=>['pending','waiting','requested'].includes(a.status||'pending')&&(!venture||tasks.get(a.task_id)?.venture_id===venture));if(!list.length)return empty(host,'No decisions waiting. Actions requiring approval will appear here.');for(const a of list){const row=el('article',null,'record');row.dataset.approvalId=a.id;const top=el('div',null,'record-top');top.append(el('h3',a.action||'Requested action'),status(a.status||'pending'));row.append(top,el('p',tasks.get(a.task_id)?.title||a.task_id||''),el('pre',stringify(a.details)));const controls=el('div',null,'record-actions');for(const decision of ['approved','denied'])controls.append(button(decision==='approved'?'Approve action':'Deny',()=>mutate('/api/approvals/'+encodeURIComponent(a.id),{decision},decision==='approved'?'Action approved.':'Action denied.'),decision==='approved'?'primary':'secondary danger'));controls.append(button('Inspect objective',()=>openTask(a.task_id),'text-button'));row.append(controls);host.append(row);}}
  function renderKnowledge(host,items,kind){host.replaceChildren();if(!items.length)return empty(host,kind==='memory'?'No saved company memory yet.':'No opportunities recorded yet.');for(const item of [...items].reverse()){const row=el('article',null,'record');const top=el('div',null,'record-top');top.append(el('h3',item.title));if(item.status)top.append(status(item.status));row.append(top,el('p',item.content||item.summary),el('div',date(item.created_at),'record-meta'));host.append(row);}}
  function renderArtifacts(host,items){host.replaceChildren();if(!items.length)return empty(host,'No artifacts yet. Files will appear after an execution produces them.');for(const a of [...items].reverse()){const row=el('article',null,'record');const link=el('a',a.name||a.path||a.id,'artifact-link');link.href='/api/artifacts/'+encodeURIComponent(a.id);link.target='_blank';link.rel='noopener';row.append(link,el('div',[a.task_id,date(a.created_at)].filter(Boolean).join(' · '),'record-meta'));host.append(row);}}
  function providers(){if(Array.isArray(state.providers))return state.providers.map(p=>typeof p==='string'?{id:p,name:p}:p);return Object.entries(state.providers||{}).map(([id,p])=>typeof p==='object'?{id,...p}:{id,name:id,configured:Boolean(p)});}
  function providerId(p){return p.id||p.provider||p.name;}
  function providerReady(p){return Boolean(p.configured??p.available??p.ready??p.enabled);}
  function renderProviders(){const host=$('provider-list');host.replaceChildren();const list=providers();if(!list.length)empty(host,'No model provider is configured. Add a session key below.');for(const p of list){const row=el('div',null,'record');const top=el('div',null,'record-top');top.append(el('h3',p.name||providerId(p)),status(providerReady(p)?'configured':'not_configured'));row.append(top);const env=p.env_var||p.env_key||p.key_env||({openai:'OPENAI_API_KEY',anthropic:'ANTHROPIC_API_KEY',gemini:'GEMINI_API_KEY',google:'GEMINI_API_KEY'}[providerId(p)]);if(!providerReady(p))row.append(el('p',env?`Add a session key below, or set ${env} before launching Genesis.`:p.setup||'Add a session key below.'));if(p.base_url)row.append(el('div',p.base_url,'record-meta'));host.append(row);}const anyReady=list.some(providerReady);$('setup-notice').hidden=anyReady;if(!anyReady)$('setup-notice').textContent='Model setup required. Open Agents & controls to add a provider key for this session. Objectives cannot execute model work until a provider is available.';if(!credentialsInitialized){$('credentials-configure-agents').checked=false;credentialsInitialized=true;}}
  function syncAgentChoices(){
    const role=$('objective-role'),agents=availableAgents();
    const signature=JSON.stringify(agents.map(a=>[a.id||a.role,a.name]));
    if(role.dataset.signature===signature)return;
    const prior=role.value;role.replaceChildren();
    for(const a of agents){const opt=el('option',`${a.name||a.role} | ${a.id||a.role}`);opt.value=a.id||a.role;role.append(opt);}
    if([...role.options].some(o=>o.value===prior))role.value=prior;
    role.dataset.signature=signature;
  }
  function renderAgents(){
    syncAgentChoices();
    const agents=arr(state.agents);
    const signature=JSON.stringify([venture,state.team_memberships,agents])+JSON.stringify(providers().map(p=>[providerId(p),p.model_catalog]));
    if(signature===agentSignature)return;
    const host=$('agent-list');
    if(host.contains(document.activeElement)||host.querySelector('form[data-dirty="true"]'))return;
    agentSignature=signature;host.replaceChildren();
    for(const a of agents){
      const form=el('form',null,'item-card agent-form');form.dataset.role=a.role;form.dataset.agentId=a.id||a.role;
      for(const event of ['input','change'])form.addEventListener(event,()=>{form.dataset.dirty='true';});
      form.append(el('h3',a.name||a.role),el('p',a.description||'Configured agent role.','muted'));
      const pl=el('label','Provider');const select=el('select');select.name='provider';
      const ids=new Set(providers().map(providerId));if(a.provider)ids.add(a.provider);
      for(const id of ids){const o=el('option',id);o.value=id;select.append(o);}
      if(!ids.size){const o=el('option','No providers available');o.value='';select.append(o);}
      select.value=a.provider||select.value;pl.append(select);
      const ml=el('label','Model');const modelSelect=el('select');modelSelect.name='model';ml.append(modelSelect);
      const customLabel=el('label','Custom model identifier');const input=el('input');input.name='custom_model';input.placeholder='Exact provider model ID';customLabel.append(input);
      const rl=el('label','Reasoning effort');const effort=el('select');effort.name='reasoning_effort';rl.append(effort);
      const priceInfo=el('p','','muted');priceInfo.dataset.modelPricing='';
      function catalog(){return arr(providers().find(p=>providerId(p)===select.value)?.model_catalog);}
      function selectedModel(){return modelSelect.value==='__custom__'?input.value.trim():modelSelect.value;}
      function updateEfforts(prior=''){
        const item=catalog().find(m=>m.id===selectedModel());effort.replaceChildren();
        const initial=el('option','Provider default / legacy setting');initial.value='';effort.append(initial);
        for(const value of arr(item?.reasoning_efforts)){const o=el('option',value);o.value=value;effort.append(o);}
        if(prior&&!arr(item?.reasoning_efforts).includes(prior)){const o=el('option',prior+' (saved override)');o.value=prior;effort.append(o);}
        effort.value=prior;
        customLabel.hidden=modelSelect.value!=='__custom__';input.required=!customLabel.hidden;
        const price=item?.pricing;
        priceInfo.textContent=price?`Published-price estimate rates / million tokens: input ${money(price.input_cost_per_million)}, cached input ${price.cached_input_cost_per_million==null?'unavailable':money(price.cached_input_cost_per_million)}, output ${money(price.output_cost_per_million)}. Verified ${item.verified_at||'date unavailable'}. ${item.requires_ceo_authorization?'Requires explicit Astra authorization for each objective.':''}`:'No published pricing or reasoning catalog entry for this custom model.';
        if(item?.source_url){const link=el('a',' Pricing source');link.href=item.source_url;link.target='_blank';link.rel='noopener';priceInfo.append(link);}
      }
      function updateModels(value){
        modelSelect.replaceChildren();for(const m of catalog()){const o=el('option',m.label||m.id);o.value=m.id;modelSelect.append(o);}
        const custom=el('option','Custom / existing model');custom.value='__custom__';modelSelect.append(custom);
        modelSelect.value=catalog().some(m=>m.id===value)?value:'__custom__';input.value=modelSelect.value==='__custom__'?(value||''):'';
        updateEfforts(value===a.model?(a.reasoning_effort||''):'');
      }
      updateModels(a.model);
      select.addEventListener('change',()=>updateModels(''));
      modelSelect.addEventListener('change',()=>updateEfforts(''));
      input.addEventListener('input',()=>updateEfforts(effort.value));
      form.append(pl,ml,customLabel,rl,priceInfo);
      for(const [field,label] of [['input_cost_per_million','Conservative budget input rate (USD / million tokens)'],['output_cost_per_million','Conservative budget output rate (USD / million tokens)']]){
        const labelNode=el('label',label);const rate=el('input');rate.name=field;rate.type='number';rate.min='0.001';rate.max='100000';rate.step='0.001';rate.required=true;rate.value=a[field]??(field.startsWith('input')?10:30);labelNode.append(rate);form.append(labelNode);
      }
      const fl=el('label','Fallback routes (optional JSON, maximum two)');const fallbacks=el('textarea');fallbacks.name='fallbacks';fallbacks.rows=3;fallbacks.value=JSON.stringify(a.fallbacks||[],null,2);fallbacks.placeholder='[{"provider":"anthropic","model":"model-id"}]';fl.append(fallbacks);form.append(fl);
      form.append(el('p','Conservative budget rates control reservations and charges. Published pricing is separate reporting data; it never changes these enforcement rates. Fallback requests may also incur charges.','muted'));
      const save=el('button','Save configuration','secondary');save.type='submit';form.append(save);
      form.addEventListener('submit',e=>{e.preventDefault();run(save,async()=>{
        let routes;try{routes=JSON.parse(fallbacks.value.trim()||'[]');}catch{throw new Error('Fallback routes must be valid JSON.');}
        if(!Array.isArray(routes)||routes.length>2||routes.some(r=>!r||typeof r!=='object'||Array.isArray(r)||Object.keys(r).some(k=>!['model','provider','reasoning_effort'].includes(k))||(r.reasoning_effort!=null&&typeof r.reasoning_effort!=='string')||!['openai','anthropic','gemini'].includes(r.provider)||typeof r.model!=='string'||!r.model.trim()))throw new Error('Use at most two fallback objects, each with a supported provider, a model identifier and optional reasoning_effort.');
        await mutate('/api/agents/'+encodeURIComponent(a.id||a.role),{provider:select.value,model:selectedModel(),reasoning_effort:effort.value||null,input_cost_per_million:Number(form.elements.input_cost_per_million.value),output_cost_per_million:Number(form.elements.output_cost_per_million.value),fallbacks:routes},'Agent configuration saved.');
        form.dataset.dirty='false';agentSignature='';form.querySelector(':focus')?.blur();resetObjectiveAuthorization();renderAgents();schedulePreview();
      });});host.append(form);
    }
    if(!agents.length)empty(host,'Agent roles are not available yet.');
  }
  function lines(id){return $(id).value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);}
  function objectiveAssignment(){const agent=arr(state?.agents).find(a=>(a.id||a.role)===$('objective-role').value);return {agent_id:agent?.id||agent?.role||$('objective-role').value,role:agent?.role||'coo'};}
  function agentAttribution(task){const agent=arr(state?.agents).find(a=>(a.id||a.role)===task.agent_id);return task.agent_id?`${agent?.name||task.agent_name||task.role} [${task.agent_id}] · ${task.role}`:task.role;}
  function availableAgents(){return arr(state?.agents).filter(a=>{if(a.enabled===false)return false;const legacy=(a.id||a.role)===a.role;if(!venture)return legacy||!arr(state.team_memberships).some(m=>m.agent_id===(a.id||a.role)&&m.status==='active');const membership=arr(state.team_memberships).find(m=>m.venture_id===venture&&m.agent_id===(a.id||a.role));return membership?membership.enabled!==false&&membership.status!=='removed':legacy;});}
  function field(form,name,label,value='',type='text'){const l=el('label',label),input=el(type==='textarea'?'textarea':'input');input.name=name;if(type==='textarea')input.rows=3;else input.type=type;input.value=value??'';if(type==='number'){input.min='0';input.step='0.01';}l.append(input);form.append(l);return input;}
  function renderTeam(){
    const members=arr(state.team_memberships).filter(m=>m.venture_id===venture&&m.status!=='removed');
    const signature=JSON.stringify([venture,state.agents,state.role_templates,state.team_memberships,state.ventures,state.tasks,state.settings]);
    const host=$('team-list');if(signature===teamSignature||(host.dataset.projectId===venture&&((host.contains(document.activeElement)&&document.activeElement.matches('input,textarea,select'))||host.querySelector('form[data-dirty="true"]'))))return;teamSignature=signature;host.dataset.projectId=venture;
    $('team-controls').hidden=!venture;$('team-project-notice').textContent=venture?'Members are specific agent instances. Removing a member preserves tasks, charges and history.':'Select a project in the workspace selector to manage its team.';
    const templates=$('team-template'),priorTemplate=templates.value;templates.replaceChildren();
    for(const t of arr(state.role_templates)){const o=el('option',t.name||t.id);o.value=t.id;templates.append(o);}if([...templates.options].some(o=>o.value===priorTemplate))templates.value=priorTemplate;
    const editor=$('role-template-edit'),priorEdit=editor.value;editor.replaceChildren(el('option','Create a new template'));editor.firstChild.value='';for(const t of arr(state.role_templates)){const o=el('option',t.name||t.id);o.value=t.id;editor.append(o);}if([...editor.options].some(o=>o.value===priorEdit))editor.value=priorEdit;if(!$('role-template-model').options.length)templateModels();
    const assign=$('team-existing'),priorAssign=assign.value;assign.replaceChildren();for(const a of arr(state.agents).filter(a=>!members.some(m=>m.agent_id===(a.id||a.role)))){const o=el('option',`${a.name} · ${a.role} · ${a.id||a.role}`);o.value=a.id||a.role;assign.append(o);}if([...assign.options].some(o=>o.value===priorAssign))assign.value=priorAssign;
    const project=arr(state.ventures).find(v=>v.id===venture);if(document.activeElement!==$('project-budget'))$('project-budget').value=project?.budget_usd??'';if(document.activeElement!==$('project-policy')&&!$('project-policy-form').dataset.dirty)$('project-policy').value=project?.operating_policy??'';if(project)$('team-project-notice').textContent+=` Project charges ${money(project.spent_usd)} · Reserved ${money(project.reserved_usd)}.`;
    renderProjectPreparation(project);
    host.replaceChildren();if(!venture)return;if(!members.length)empty(host,'This project has no assigned agents. Add only the roles this project needs.');
    for(const m of members){
      const a=arr(state.agents).find(a=>(a.id||a.role)===m.agent_id);if(!a)continue;
      const form=el('form',null,'item-card team-agent-form');form.dataset.agentId=a.id||a.role;
      for(const event of ['input','change'])form.addEventListener(event,()=>{form.dataset.dirty='true';});
      form.append(el('h3',`${a.name} · ${a.role}`),el('p',`Agent ID: ${a.id||a.role}`,'record-meta'),status(a.activity_status||'idle'),el('p',`Agent charges ${money(a.spent_usd)} · Reserved ${money(a.reserved_usd)}`,'muted'));
      const globals=el('details');globals.append(el('summary','Global agent identity and defaults (all projects)'));form.append(globals);const name=field(globals,'name','Global agent name',a.name),specialization=field(globals,'specialization','Global specialization',a.specialization),instructions=field(globals,'system_instructions','Global system instructions',a.system_instructions,'textarea'),budget=field(globals,'budget_usd','Global agent budget (USD, blank inherits company budget)',a.budget_usd,'number');globals.append(button('Save global agent defaults',async()=>{await mutate('/api/agents/'+encodeURIComponent(a.id||a.role),{name:name.value.trim(),specialization:specialization.value,system_instructions:instructions.value,budget_usd:budget.value===''?null:Number(budget.value)},'Global agent defaults saved for all projects.');}));const projectSpecialization=field(form,'project_specialization','Venture specialization',m.specialization??a.specialization,'textarea'),projectInstructions=field(form,'project_system_instructions','Venture system instructions',m.system_instructions??a.system_instructions,'textarea'),responsibilities=field(form,'responsibilities','Project responsibilities',m.responsibilities,'textarea');form.append(el('p','Venture instructions and specialization apply only to this membership. Global defaults remain separate.','muted'));
      const enabledLabel=el('label',null,'check'),enabled=el('input');enabled.type='checkbox';enabled.name='enabled';enabled.checked=m.enabled!==false&&a.enabled!==false;enabledLabel.append(enabled,el('span','Enabled in this project'));form.append(enabledLabel);
      const overrideLabel=el('label',null,'check'),override=el('input');override.type='checkbox';override.name='use_override';override.checked=Boolean(m.overrides&&Object.keys(m.overrides).length);overrideLabel.append(override,el('span','Override provider / model for this project'));form.append(overrideLabel);
      const route=m.overrides||{},providerLabel=el('label','Project provider'),provider=el('select');provider.name='provider';for(const p of providers()){const o=el('option',providerId(p));o.value=providerId(p);provider.append(o);}provider.value=route.provider||a.provider;providerLabel.append(provider);form.append(providerLabel);
      const modelLabel=el('label','Project model'),model=el('select');model.name='model';modelLabel.append(model);form.append(modelLabel);const custom=field(form,'custom_model','Custom project model',route.model||a.model);
      const effortLabel=el('label','Project reasoning effort'),effort=el('select');effort.name='reasoning_effort';effortLabel.append(effort);form.append(effortLabel);
      function efforts(value){const entry=arr(providers().find(p=>providerId(p)===provider.value)?.model_catalog).find(x=>x.id===model.value);effort.replaceChildren();for(const optionValue of new Set(['',...arr(entry?.reasoning_efforts),...(value?[value]:[])])){const o=el('option',optionValue||'Provider default');o.value=optionValue;effort.append(o);}effort.value=value||'';custom.parentElement.hidden=model.value!=='__custom__';}
      function models(value){model.replaceChildren();for(const entry of arr(providers().find(p=>providerId(p)===provider.value)?.model_catalog)){const o=el('option',entry.label||entry.id);o.value=entry.id;model.append(o);}const o=el('option','Custom / existing model');o.value='__custom__';model.append(o);model.value=[...model.options].some(o=>o.value===value)?value:'__custom__';custom.value=value||'';efforts(route.reasoning_effort||a.reasoning_effort||'');}
      models(route.model||a.model);provider.addEventListener('change',()=>models(''));model.addEventListener('change',()=>efforts(''));
      const save=el('button','Save project agent','secondary');save.type='submit';form.append(save);
      form.addEventListener('submit',e=>{e.preventDefault();run(save,async()=>{await mutate('/api/projects/'+encodeURIComponent(venture)+'/team/'+encodeURIComponent(a.id||a.role),{enabled:enabled.checked,specialization:projectSpecialization.value,system_instructions:projectInstructions.value,responsibilities:responsibilities.value,overrides:override.checked?{provider:provider.value,model:model.value==='__custom__'?custom.value.trim():model.value,reasoning_effort:effort.value||null}:{}},'Project agent saved.');form.dataset.dirty='false';form.querySelector(':focus')?.blur();teamSignature='';renderTeam();});});
      const controls=el('div',null,'record-actions');controls.append(button('Duplicate agent',()=>mutate('/api/agents/'+encodeURIComponent(a.id||a.role)+'/duplicate',{name:a.name+' copy',project_ids:[venture]},'Independent agent copy created.')),button('Remove from project',()=>mutate('/api/projects/'+encodeURIComponent(venture)+'/team/'+encodeURIComponent(a.id||a.role),{action:'remove'},'Membership removed; history preserved.'),'secondary danger'));form.append(controls);host.append(form);
      const history=el('details'),historyHost=el('div');history.append(el('summary','Agent task history'),historyHost);renderTasks(historyHost,arr(state.tasks).filter(t=>t.venture_id===venture&&((t.agent_id||t.role)===(a.id||a.role)||arr(t.agent_history).includes(a.id||a.role))));form.append(history);
    }
  }
  $('team-add-form').addEventListener('submit',e=>{e.preventDefault();if(!venture)return;run(e.currentTarget.querySelector('[type=submit]'),async()=>{await mutate('/api/agents',{template_id:$('team-template').value,name:$('team-agent-name').value.trim(),specialization:$('team-specialization').value,project_ids:[venture]},'Project agent created.');$('team-agent-name').value='';$('team-specialization').value='';});});
  $('team-assign-form').addEventListener('submit',e=>{e.preventDefault();if(venture)run(e.currentTarget.querySelector('[type=submit]'),()=>mutate('/api/projects/'+encodeURIComponent(venture)+'/team',{agent_id:$('team-existing').value,enabled:true},'Agent assigned to project.'));});
  $('project-budget-form').addEventListener('submit',e=>{e.preventDefault();if(venture)run(e.currentTarget.querySelector('[type=submit]'),()=>mutate('/api/projects/'+encodeURIComponent(venture),{budget_usd:$('project-budget').value===''?null:Number($('project-budget').value)},'Project budget saved.'));});

  $('project-policy-form').addEventListener('input',()=>{$('project-policy-form').dataset.dirty='true';});
  $('project-policy-form').addEventListener('submit',e=>{e.preventDefault();if(venture)run(e.currentTarget.querySelector('[type=submit]'),async()=>{await mutate('/api/projects/'+encodeURIComponent(venture),{operating_policy:$('project-policy').value},'Venture operating policy saved.');delete $('project-policy-form').dataset.dirty;});});
  function renderProjectPreparation(project){
    const limits=project?.execution_limits||{},global=state.settings||{};
    if(!$('project-limits-form').dataset.dirty)for(const key of projectLimitKeys)$('project-limit-'+key).value=limits[key]??'';
    $('project-limits-summary').textContent='Effective project limits: '+projectLimitKeys.map(key=>`${key.replaceAll('_',' ')} ${key==='max_concurrency'?Math.min(limits[key]??global[key]??1,global[key]??1):limits[key]??global[key]??'unavailable'}`).join(' | ')+`. Global worker capacity: ${global.max_concurrency??1} concurrent task(s). Project concurrency cannot exceed available global capacity.`;
    const draft=project?.mission_draft,agentSelect=$('project-mission-agent');
    if(!$('project-mission-form').dataset.dirty){agentSelect.replaceChildren();for(const agent of availableAgents()){const option=el('option',`${agent.name} | ${agent.id||agent.role}`);option.value=agent.id||agent.role;agentSelect.append(option);}$('project-mission-objective').value=draft?.objective||'';if(draft?.agent_id)agentSelect.value=draft.agent_id;$('project-mission-mode').value=draft?.work_mode||'independent';}
    $('project-mission-status').textContent=draft?'Prepared draft only: awaiting separate CEO spending authorization and provider readiness before execution.':'No prepared mission saved.';
    $('load-prepared-mission').disabled=!draft;
  }
  function loadPreparedMission(){
    const draft=arr(state?.ventures).find(v=>v.id===venture)?.mission_draft;if(!draft)throw new Error('No prepared mission is saved for this project.');
    if(!availableAgents().some(a=>(a.id||a.role)===draft.agent_id))throw new Error('The prepared lead agent is not currently enabled in this project.');
    $('objective').value=draft.objective;$('objective-role').value=draft.agent_id;$('objective-mode').value=draft.work_mode;
    for(const id of ['objective-depends','objective-reviews','objective-files'])$(id).value='';
    resetObjectiveAuthorization();syncObjectiveRoute();schedulePreview();showView('overview');
    feedback('Prepared mission loaded for review. No task was submitted; separate spending authorization and individual action approvals still apply.');
  }
  for(const id of ['project-limits-form','project-mission-form'])for(const event of ['input','change'])$(id).addEventListener(event,()=>{$(id).dataset.dirty='true';});
  $('project-limits-form').addEventListener('submit',e=>{e.preventDefault();if(!venture)return;run(e.currentTarget.querySelector('[type=submit]'),async()=>{const execution_limits={};for(const key of projectLimitKeys){const value=$('project-limit-'+key).value;if(value!=='')execution_limits[key]=Number(value);}await mutate('/api/projects/'+encodeURIComponent(venture),{execution_limits},'Project execution limits saved; approvals unchanged.');delete $('project-limits-form').dataset.dirty;teamSignature='';renderTeam();});});
  $('project-mission-form').addEventListener('submit',e=>{e.preventDefault();if(!venture)return;run(e.currentTarget.querySelector('[type=submit]'),async()=>{const objective=$('project-mission-objective').value.trim();await mutate('/api/projects/'+encodeURIComponent(venture),{mission_draft:objective?{objective,agent_id:$('project-mission-agent').value,work_mode:$('project-mission-mode').value}:null},'Mission draft saved. No task submitted or spending authorized.');delete $('project-mission-form').dataset.dirty;teamSignature='';renderTeam();});});
  $('load-prepared-mission').addEventListener('click',()=>run($('load-prepared-mission'),loadPreparedMission));
  function documentBase(){return '/api/projects/'+encodeURIComponent(venture)+'/documents';}
  function renderDocuments(){
    const host=$('document-list'),docs=arr(state.venture_documents).filter(d=>d.venture_id===venture),signature=JSON.stringify([venture,docs]);
    $('document-controls').hidden=!venture;$('document-notice').textContent=venture?'Reference documents are read-only for agents. Decisions are maintained by the CEO. Revisions preserve prior content.':'Select a venture to manage its durable documents.';
    if(signature===documentSignature)return;documentSignature=signature;host.replaceChildren();
    if(!venture){$('document-editor').hidden=true;return;}if(!docs.length)empty(host,'No venture documents yet.');
    for(const doc of docs){const row=el('article',null,'record');row.dataset.documentId=doc.id;row.append(button(doc.name,()=>openDocument(doc.id),'record-title'),el('p',`${doc.kind} | Revision ${doc.revision} | ${doc.read_only?'Read-only for agents':'Agent revisions permitted'}`,'record-meta'));host.append(row);}
    if(selectedDocument&&selectedDocument.venture_id!==venture){selectedDocument=null;$('document-editor').hidden=true;}
  }
  async function openDocument(id){
    const project=venture,base=documentBase(),result=await api(base+'/'+encodeURIComponent(id));if(project!==venture)return;
    const doc=result.document||result;selectedDocument=doc;$('document-editor').hidden=false;$('document-name').textContent=doc.name;$('document-content').value=doc.content||'';$('document-revision').textContent=`Revision ${doc.revision} | ${doc.kind} | ${doc.read_only?'Read-only for agents; CEO may revise':'Editable working document'}`;
    $('document-download').href=base+'/'+encodeURIComponent(id)+'/download';
    const history=await api(base+'/'+encodeURIComponent(id)+'/revisions');if(project!==venture||selectedDocument?.id!==id)return;
    const host=$('document-history');host.replaceChildren();for(const rev of arr(history.revisions)){const row=el('details');row.append(el('summary',`Revision ${rev.revision??rev.version} | ${date(rev.created_at)} | ${rev.actor||rev.author||'Recorded author'}`),el('pre',rev.document?.content??rev.content??''));host.append(row);}
  }
  $('document-create-form').addEventListener('submit',e=>{e.preventDefault();if(!venture)return;const f=e.currentTarget;run(f.querySelector('[type=submit]'),async()=>{const result=await api(documentBase(),{name:f.elements.name.value.trim(),content:f.elements.content.value,kind:f.elements.kind.value,read_only:f.elements.read_only.checked});f.reset();documentSignature='';await refresh();await openDocument((result.document||result).id);feedback('Venture document created.');});});
  $('document-revise-form').addEventListener('submit',e=>{e.preventDefault();if(!selectedDocument||selectedDocument.venture_id!==venture)return;const id=selectedDocument.id;run(e.currentTarget.querySelector('[type=submit]'),async()=>{await api(documentBase()+'/'+encodeURIComponent(id),{content:$('document-content').value,expected_revision:selectedDocument.revision});documentSignature='';await refresh();await openDocument(id);feedback('Document revision saved.');});});

  function templateEfforts(value=''){const entry=arr(providers().find(p=>providerId(p)===$('role-template-provider').value)?.model_catalog).find(m=>m.id===$('role-template-model').value);const select=$('role-template-effort');select.replaceChildren();for(const v of new Set(['',...arr(entry?.reasoning_efforts),...(value?[value]:[])])){const o=el('option',v||'Provider default');o.value=v;select.append(o);}select.value=value;$('role-template-custom-label').hidden=$('role-template-model').value!=='__custom__';}
  function templateModels(value=''){const select=$('role-template-model');select.replaceChildren();for(const m of arr(providers().find(p=>providerId(p)===$('role-template-provider').value)?.model_catalog)){const o=el('option',m.label||m.id);o.value=m.id;select.append(o);}const o=el('option','Custom model');o.value='__custom__';select.append(o);if(value){select.value=[...select.options].some(o=>o.value===value)?value:'__custom__';$('role-template-custom').value=value;}templateEfforts();}
  $('role-template-provider').addEventListener('change',()=>templateModels());
  $('role-template-model').addEventListener('change',()=>templateEfforts());
  $('role-template-edit').addEventListener('change',()=>{const f=$('role-template-form'),template=arr(state.role_templates).find(t=>t.id===$('role-template-edit').value);for(const key of ['name','description','system_instructions'])f.elements[key].value=template?.[key]||'';$('role-template-provider').value=template?.provider||'openai';templateModels(template?.model||'');templateEfforts(template?.reasoning_effort||'');});
  $('role-template-form').addEventListener('submit',e=>{e.preventDefault();const f=e.currentTarget,id=$('role-template-edit').value,body={...Object.fromEntries(new FormData(f)),provider:$('role-template-provider').value,model:$('role-template-model').value==='__custom__'?$('role-template-custom').value.trim():$('role-template-model').value,reasoning_effort:$('role-template-effort').value||null};run(f.querySelector('[type=submit]'),async()=>{await mutate('/api/role-templates'+(id?'/'+encodeURIComponent(id):''),body,id?'Role template defaults saved. Existing agent instances retain their configuration.':'Reusable role template created.');f.reset();f.querySelector(':focus')?.blur();teamSignature='';renderTeam();});});
  function eventDetails(event){const {id,action,type,event:kind,created_at,timestamp,...details}=event;return Object.keys(details).length?details:null;}
  function renderAudit(){const host=$('audit-list');host.replaceChildren();let list=arr(state.audit);if(venture){const ids=new Set(scoped(state.tasks).map(t=>t.id));list=list.filter(a=>a.venture_id===venture||ids.has(a.task_id)||ids.has(a.entity_id));}if(!list.length)return empty(host,'No recorded activity yet.');for(const event of [...list].sort((a,b)=>String(b.created_at||b.timestamp).localeCompare(String(a.created_at||a.timestamp))).slice(0,150)){const row=el('article',null,'record');const top=el('div',null,'record-top');top.append(el('h3',event.action||event.type||event.event||'System event'),el('span',date(event.created_at||event.timestamp),'muted'));row.append(top);const details=eventDetails(event);if(details)row.append(el('pre',stringify(details)));host.append(row);}}
  function render(){if(!state)return;const ventures=arr(state.ventures);const options=JSON.stringify(ventures.map(v=>[v.id,v.name]));if($('venture-select').dataset.signature!==options){$('venture-select').replaceChildren(el('option','All ventures'));$('venture-select').firstChild.value='';for(const v of ventures){const o=el('option',v.name);o.value=v.id;$('venture-select').append(o);}$('venture-select').dataset.signature=options;}if(venture&&!ventures.some(v=>v.id===venture))venture='';$('venture-select').value=venture;$('workspace-name').textContent=ventures.find(v=>v.id===venture)?.name||'All ventures';const tasks=scoped(state.tasks);const pending=arr(state.approvals).filter(a=>['pending','waiting','requested'].includes(a.status||'pending')&&(!venture||tasks.some(t=>t.id===a.task_id)));$('task-count').textContent=tasks.length||'';$('metric-active').textContent=tasks.filter(t=>['queued','running','waiting_approval','waiting_children'].includes(t.status)).length;$('metric-completed').textContent=tasks.filter(t=>t.status==='completed').length;$('metric-approvals').textContent=pending.length;const s=state.settings||{};$('metric-budget').textContent=money(Math.max(0,Number(s.budget_usd||0)-Number(s.spent_usd||0)-Number(s.reserved_usd||0)));renderAccounting(s);renderFinance();renderTasks($('recent-tasks'),tasks,5);renderTasks($('all-tasks'),tasks);renderApprovals($('approval-list'));renderApprovals($('all-approvals'));const vl=$('venture-list');vl.replaceChildren();const vs=ventures.filter(v=>!venture||v.id===venture);if(!vs.length)empty(vl,'No ventures yet. Create a venture to organize objectives and knowledge.');for(const v of vs){const card=el('article',null,'item-card');card.append(el('h3',v.name),el('p',v.description,'muted'),el('div',`${arr(state.tasks).filter(t=>t.venture_id===v.id).length} objectives`,'record-meta'));if(v.status)card.append(status(v.status));vl.append(card);}renderKnowledge($('memory-list'),scoped(state.memories),'memory');renderKnowledge($('opportunity-list'),scoped(state.opportunities),'opportunity');const ids=new Set(tasks.map(t=>t.id));renderArtifacts($('artifact-list'),arr(state.artifacts).filter(a=>!venture||a.venture_id===venture||ids.has(a.task_id)));renderProviders();renderPricing();renderAgents();renderTeam();renderDocuments();syncObjectiveRoute();renderAudit();if(requestedMission){requestedMission=false;const url=new URL(location.href);url.searchParams.delete('mission');history.replaceState(null,'',url);run(null,loadPreparedMission);}if(!settingsInitialized){$('budget-usd').value=s.budget_usd??0;$('max-steps').value=s.max_steps??10;$('max-concurrency').value=s.max_concurrency??1;$('max-delegation-depth').value=s.max_delegation_depth??3;$('max-delegated-tasks').value=s.max_delegated_tasks??12;$('allow-network').checked=Boolean(s.allow_network);$('allow-terminal').checked=Boolean(s.allow_terminal);settingsInitialized=true;}}
  async function refresh(){if(refreshBusy)return;refreshBusy=true;try{state=await api('/api/state');render();$('connection').textContent='Connected to local server';$('connection-dot').classList.add('online');$('updated').textContent='Updated '+new Date().toLocaleTimeString(undefined,{hour:'2-digit',minute:'2-digit'});}catch(e){$('connection').textContent='Server unavailable';$('connection-dot').classList.remove('online');feedback(e.message,true);}finally{refreshBusy=false;}}
  let pricingSignature='';
  function renderPricing(){
    const models=arr(providers().find(p=>providerId(p)==='openai')?.model_catalog);
    const signature=JSON.stringify(models);if(signature===pricingSignature||$('pricing-form').contains(document.activeElement))return;
    pricingSignature=signature;const select=$('pricing-model'),prior=select.value;select.replaceChildren();
    for(const m of models){const o=el('option',m.label||m.id);o.value=m.id;select.append(o);}if(models.some(m=>m.id===prior))select.value=prior;
    updatePricingFields();
  }
  function updatePricingFields(){
    const item=arr(providers().find(p=>providerId(p)==='openai')?.model_catalog).find(m=>m.id===$('pricing-model').value);
    const p=item?.pricing||{};$('pricing-input').value=p.input_cost_per_million??'';$('pricing-cached').value=p.cached_input_cost_per_million??'';$('pricing-output').value=p.output_cost_per_million??'';
    const host=$('pricing-source');host.replaceChildren(el('span',`Verified ${item?.verified_at||'unavailable'}. ${item?.pricing_override||item?.override||p.override?'Local reporting override.':'Published catalog prices.'} `));
    if(item?.source_url){const link=el('a','Pricing source');link.href=item.source_url;link.target='_blank';link.rel='noopener';host.append(link);}
  }
  $('pricing-model').addEventListener('change',updatePricingFields);
  $('pricing-form').addEventListener('submit',e=>{e.preventDefault();run(e.currentTarget.querySelector('[type=submit]'),async()=>{
    await mutate('/api/pricing',{model:$('pricing-model').value,input_cost_per_million:Number($('pricing-input').value),cached_input_cost_per_million:Number($('pricing-cached').value),output_cost_per_million:Number($('pricing-output').value)},'Reporting prices saved. Conservative budget rates unchanged.');
    $('pricing-form').querySelector(':focus')?.blur();pricingSignature='';renderPricing();
  });});
  function renderAccounting(settings){
    const a=state.accounting||{};
    const charged=a.conservative_charged_usd??settings.spent_usd;
    const reserved=a.reserved_usd??settings.reserved_usd;
    $('metric-spent').textContent=`Internal safety estimate ${money(charged)} (not the OpenAI bill) | Current reservation ${money(reserved)}`;
    const lines=[`Internal safety budget used: ${money(charged)} (not the OpenAI bill)`,`Current reservation: ${money(reserved)}`,`Published-price estimate: ${a.estimated_cost_usd==null?'unavailable':money(a.estimated_cost_usd)}${a.estimate_complete===false?' (incomplete)':''}`,`Provider token usage: ${a.input_tokens??0} input | ${a.cached_input_tokens??0} known recorded cached input | ${a.output_tokens??0} output | ${a.reasoning_output_tokens??0} reasoning output`, `Request cycles: ${a.request_count??0} | Responses: ${a.response_count??0} | Known billable attempts: ${a.known_billable_attempt_count??a.response_count??0} | Unknown-usage attempts: ${a.unknown_usage_attempts??0} | Unpriced responses: ${a.unpriced_responses??0}`,...(a.cache_usage_unknown_responses?[`Cache details unavailable for ${a.cache_usage_unknown_responses} responses; estimate assumes uncached input.`]:[]),`Pricing basis: ${a.pricing_basis||'unavailable'}`,`Genesis-attributed official billed amount: ${a.official_billed_usd==null?'unavailable':money(a.official_billed_usd)}`,`Budget: ${money(settings.budget_usd)}`];
    $('usage-detail').textContent=lines.join('\n');$('accounting-summary').textContent=lines.join('\n');
  }
  let billingSettingsSignature='';
  function renderFinance(){
    const settings=state.settings||{},accounting=state.accounting||{},billing=state.billing||{},report=billing.report,costs=report?.costs;
    $('finance-charged').textContent=money(accounting.conservative_charged_usd??settings.spent_usd);
    $('finance-reserved').textContent=`Internal reservation ${money(accounting.reserved_usd??settings.reserved_usd)} | Internal safety budget remaining ${money(Math.max(0,Number(settings.budget_usd||0)-Number(settings.spent_usd||0)-Number(settings.reserved_usd||0)))}`;
    $('finance-explanation').textContent=`OpenAI reports your actual organization spending. The ${money(accounting.conservative_charged_usd??settings.spent_usd)} internal safety estimate uses deliberately cautious rates to protect the Genesis budget. It can be much higher than the actual bill and does not represent prepaid credits consumed.`;
    $('finance-estimated').textContent=accounting.estimated_cost_usd==null?'Unavailable':money(accounting.estimated_cost_usd);
    $('finance-estimate-basis').textContent=`Published-price estimate${accounting.estimate_complete===false?' | incomplete':''}; not an invoice`;
    const providerMoney=(value)=>!costs?.currency?`${value??'Unavailable'} (currency unavailable)`:costs.currency.toLowerCase()!=='usd'?`${value} ${costs.currency.toUpperCase()}`:money(value);
    const emptyCostReport=costs?.complete===true&&costs.total===0&&!costs.currency&&Object.keys(costs.daily||{}).length===0;
    const reportMonth=report?.month||(typeof report?.period_start==='string'?report.period_start.slice(0,7):'');
    $('finance-official-label').textContent=report?`Official OpenAI costs | Reported UTC month ${reportMonth||'unknown'}`:'Official OpenAI costs | UTC month to date';
    $('finance-official').textContent=emptyCostReport?'No cost amounts reported yet':costs?.total==null?'Unavailable':`${providerMoney(costs.total)}${costs.complete===false?' (partial)':''}`;
    const error=billing.error?stringify(billing.error):'';
    $('billing-status').textContent=[billing.in_flight?'Synchronization in progress.':!billing.credential_configured?'Separate Organization Admin credential is not configured.':report?'Official provider report available.':'No official report synchronized yet.',billing.historical_snapshot?'Historical stored provider snapshot; no current session Admin credential. Refresh requires separate Admin configuration.':'',billing.stale?'Saved report is stale; retain its timestamp when comparing figures.':'',costs?.complete===false?`Partial report: ${costs.missing_amount_count??'some'} missing or unrecognized cost amounts are excluded; known subtotal ${providerMoney(costs.known_total)} is not a complete total.`:'',error?'Last synchronization failed: '+error:''].filter(Boolean).join('\n');
    $('billing-sync').textContent=`Last successful synchronization: ${billing.last_successful_sync||report?.last_successful_sync||'Never'}${billing.last_attempt?' | Last attempt: '+billing.last_attempt:''}${billing.next_refresh_at?' | Next bounded refresh: '+new Date(billing.next_refresh_at*1000).toISOString():''}`;
    $('billing-window').textContent=report?`Reported window (UTC): ${report.period_start} to ${report.period_end}. Provider reporting is delayed, not instantaneous.`:'Reported window: current UTC month to date after synchronization. Before synchronization, costs are unavailable; they are never assumed zero.';
    if(emptyCostReport)$('billing-window').textContent+=' OpenAI returned no cost amounts for this window. The official OpenAI dashboard may show spending before this API report does. Usage can appear before costs; this does not establish a zero final bill or a prepaid balance.';
    $('billing-credential-status').textContent=`Server-side Organization Admin credential: ${billing.credential_configured?'configured':'not configured'}. The model API key remains separate. Configuration alone does not refresh reports.`;
    const costRows=(values,key)=>Object.entries(values||{}).map(([id,amount])=>({[key]:id,amount}));
    const showRows=(id,rows,format,none)=>{const host=$(id);host.replaceChildren();if(!arr(rows).length)return empty(host,none);for(const row of rows)host.append(el('div',format(row),'record'));};
    showRows('billing-daily',costRows(costs?.daily,'date'),row=>`${row.date||row.day||row.start_time||'Unknown date'} | ${providerMoney(row.amount??row.total??row.cost_usd)}`,'No daily provider cost report available.');
    showRows('billing-projects',costRows(costs?.by_project,'project_id'),row=>`${row.project_id||'Unattributed provider project'} | ${providerMoney(row.amount??row.total??row.cost_usd)}`,'No provider project cost attribution available.');
    showRows('billing-api-keys',costRows(costs?.by_api_key,'api_key_id'),row=>`${row.api_key_id||'Unattributed provider API key'} | ${providerMoney(row.amount)}`,'No API key cost attribution returned by the provider. Use optional completion usage for supported API key attribution.');
    const usage=report?.usage,usageHost=$('billing-usage');usageHost.replaceChildren();
    if(usage?.available===false)empty(usageHost,'Completion usage unavailable: '+(usage.error?stringify(usage.error):'not synchronized'));
    else if(usage){usageHost.append(el('p',`Completion usage only: ${usage.requests??0} requests | ${usage.input_tokens??0} input tokens | ${usage.output_tokens??0} output tokens`,'muted'));for(const group of arr(usage.groups))usageHost.append(el('div',`${group.project_id||'Unattributed project'} / ${group.api_key_id||'Unattributed API key'}${group.model?' / '+group.model:''} | ${group.requests??0} requests | ${group.input_tokens??0} input / ${group.output_tokens??0} output tokens`,'record'));}
    else empty(usageHost,'Completion usage has not been synchronized. Enable optional usage reporting to request supported API key attribution.');
    const projects=$('finance-project-budgets');projects.replaceChildren();for(const project of arr(state.ventures).filter(v=>!venture||v.id===venture)){const remaining=project.budget_usd==null?null:Math.max(0,Number(project.budget_usd)-Number(project.spent_usd||0)-Number(project.reserved_usd||0));projects.append(el('div',`${project.name} | ${remaining==null?'Inherits company budget':money(remaining)+' remaining'} | Internal safety estimate ${money(project.spent_usd)} | Reserved ${money(project.reserved_usd)}`,'record'));}if(!projects.children.length)empty(projects,'No venture budgets to display.');
    const signature=JSON.stringify(billing.config||{}),form=$('billing-settings-form');if(signature!==billingSettingsSignature&&!form.contains(document.activeElement)&&form.dataset.dirty!=='true'){billingSettingsSignature=signature;const interval=String(billing.config?.refresh_interval_seconds??0),select=$('billing-interval');if(![...select.options].some(o=>o.value===interval)){const option=el('option',`Every ${interval} seconds`);option.value=interval;select.append(option);}select.value=interval;$('billing-include-usage').checked=Boolean(billing.config?.include_usage);}
  }
  $('billing-refresh').addEventListener('click',()=>run($('billing-refresh'),async()=>{await api('/api/billing/refresh',{});await refresh();feedback('Official reporting refresh requested. Review synchronization status; this does not execute agents.');}));
  $('billing-clear').addEventListener('click',()=>run($('billing-clear'),()=>mutate('/api/billing/credentials',{clear:true},'Session Admin credential cleared. Model credentials and budgets are unchanged.')));
  $('billing-settings-form').addEventListener('change',()=>{$('billing-settings-form').dataset.dirty='true';});
  $('billing-settings-form').addEventListener('submit',e=>{e.preventDefault();run(e.currentTarget.querySelector('[type=submit]'),async()=>{await api('/api/billing/settings',{refresh_interval_seconds:Number($('billing-interval').value),include_usage:$('billing-include-usage').checked});$('billing-settings-form').dataset.dirty='false';$('billing-settings-form').querySelector(':focus')?.blur();billingSettingsSignature='';await refresh();feedback('Reporting settings saved. Budgets and model execution controls are unchanged.');});});
  function resetObjectiveAuthorization(){ $('objective-astra').checked=false; }
  function syncObjectiveRoute(){
    const a=arr(state?.agents).find(a=>(a.id||a.role)===$('objective-role').value);
    const signature=JSON.stringify([venture,a?.id,a?.provider,a?.model,a?.reasoning_effort,state?.team_memberships]);
    if(signature!==objectiveRoute){objectiveRoute=signature;resetObjectiveAuthorization();schedulePreview();}
  }
  async function previewObjective(version){
    const host=$('objective-estimate'),objective=$('objective').value.trim();
    if(!objective){host.textContent='Enter an objective to preview its route and estimated cost. Preview creates no objective and makes no provider call.';return;}
    host.textContent='Calculating local estimate...';
    try{
      const result=await api('/api/tasks/estimate',{objective,...objectiveAssignment(),work_mode:$('objective-mode').value,astra_authorized:$('objective-astra').checked,...(venture?{venture_id:venture}:{})});
      if(version!==previewVersion)return;
      host.textContent=`${result.provider} / ${result.model} | Reasoning: ${result.reasoning_effort||'provider default'}\nEstimated call cost: ${result.estimated_call_cost_usd==null?'unavailable':money(result.estimated_call_cost_usd)} | Conservative reservation: ${money(result.conservative_reservation_usd)}\nApproximate task cost: ${result.approximate_task_cost_usd==null?'unavailable':money(result.approximate_task_cost_usd)} | Maximum steps: ${result.max_steps}\n${arr(result.assumptions).join(' ')}\nLocal preview only. No provider call or task creation.`;
    }catch(e){if(version===previewVersion)host.textContent='Preview unavailable: '+e.message;}
  }
  function schedulePreview(){clearTimeout(previewTimer);const version=++previewVersion;previewTimer=setTimeout(()=>previewObjective(version),350);}
  $('objective').addEventListener('input',schedulePreview);
  $('objective-role').addEventListener('change',()=>{resetObjectiveAuthorization();syncObjectiveRoute();schedulePreview();});
  $('objective-astra').addEventListener('change',schedulePreview);
  $('objective-mode').addEventListener('change',schedulePreview);
  $('objective-form').addEventListener('submit',e=>{e.preventDefault();const objective=$('objective').value.trim();if(!objective)return;run($('submit-objective'),async()=>{const data=await api('/api/tasks',{objective,...objectiveAssignment(),work_mode:$('objective-mode').value,depends_on:lines('objective-depends'),review_of:lines('objective-reviews'),file_claims:lines('objective-files'),astra_authorized:$('objective-astra').checked,...(venture?{venture_id:venture}:{})});$('objective').value='';resetObjectiveAuthorization();schedulePreview();feedback('Objective created. Execution status will appear below.');await refresh();const task=data.task||data;if(task.id)await openTask(task.id);});});
  $('venture-form').addEventListener('submit',e=>{e.preventDefault();const f=e.currentTarget;run(f.querySelector('[type=submit]'),async()=>{const fd=new FormData(f);await mutate('/api/ventures',{name:fd.get('name').trim(),description:fd.get('description').trim()},'Venture created.');f.reset();$('venture-dialog').close();});});
  for(const kind of ['memory','opportunity'])$(kind+'-form').addEventListener('submit',e=>{e.preventDefault();const f=e.currentTarget;run(f.querySelector('[type=submit]'),async()=>{const fd=new FormData(f);const body=Object.fromEntries(fd);if(venture)body.venture_id=venture;await mutate(kind==='memory'?'/api/memories':'/api/opportunities',body,kind==='memory'?'Company memory saved.':'Opportunity added.');f.reset();});});
  $('settings-form').addEventListener('submit',e=>{e.preventDefault();run(e.currentTarget.querySelector('[type=submit]'),async()=>{await mutate('/api/settings',{budget_usd:Number($('budget-usd').value),max_steps:Number($('max-steps').value),max_concurrency:Number($('max-concurrency').value),max_delegation_depth:Number($('max-delegation-depth').value),max_delegated_tasks:Number($('max-delegated-tasks').value),allow_network:$('allow-network').checked,allow_terminal:$('allow-terminal').checked},'Execution controls saved.');});});
  $('credentials-form').addEventListener('submit',e=>{
    e.preventDefault();
    const provider=$('credentials-provider').value;
    const key=$('credentials-key').value;
    const configure_agents=$('credentials-configure-agents').checked;
    $('credentials-key').value='';
    run(e.currentTarget.querySelector('[type=submit]'),async()=>{
      try{
        await api('/api/credentials',{provider,api_key:key,configure_agents});
        feedback(configure_agents?'Session key saved and recommended routes applied to the seven legacy default agents. Existing objectives keep their route until explicitly resumed with agent settings.':'Session key saved. Review agent routes and resume blocked objectives when ready.');
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
      const t=data.task||{};const resumeRoute=JSON.stringify([id,t.provider,t.model,t.reasoning_effort,arr(state?.agents).find(a=>t.agent_id?(a.id||a.role)===t.agent_id:a.role===t.role)]);if(resumeAuthorization.task!==resumeRoute)resumeAuthorization={task:resumeRoute,checked:false};const host=$('task-detail');host.replaceChildren();$('detail-title').textContent=t.title||'Objective details';
      const heading=el('div',null,'record-top');heading.append(status(t.status),el('span',[agentAttribution(t),t.provider,t.model,t.work_mode].filter(Boolean).join(' · '),'muted'));host.append(heading,el('p',t.objective||t.title||''));
      const controls=el('div',null,'record-actions');
      const bundle=el('a','Download task ZIP','secondary');bundle.href='/api/tasks/'+encodeURIComponent(id)+'/bundle';bundle.target='_blank';bundle.rel='noopener';controls.append(bundle);
      if(!['completed','cancelled','failed'].includes(t.status))controls.append(button('Cancel objective',()=>mutate('/api/tasks/'+encodeURIComponent(id)+'/cancel',{},'Objective cancelled.'),'secondary danger'));
      if(['interrupted','blocked_credentials','blocked_budget','paused_limit','failed','blocked_agent','blocked_dependencies'].includes(t.status)){
        const authorization=el('label',null,'check');const authorize=el('input');authorize.type='checkbox';authorize.checked=resumeAuthorization.checked;authorize.addEventListener('change',()=>{resumeAuthorization.checked=authorize.checked;});authorization.append(authorize,el('span','Explicitly authorize Astra usage for this objective resume'));controls.append(authorization);
        controls.append(button('Resume objective',()=>mutate('/api/tasks/'+encodeURIComponent(id)+'/resume',{astra_authorized:resumeAuthorization.checked},'Resume requested.')));
        const baseAgent=arr(state?.agents).find(a=>t.agent_id?(a.id||a.role)===t.agent_id:a.role===t.role);
        const membership=arr(state?.team_memberships).find(m=>m.agent_id===(baseAgent?.id||baseAgent?.role)&&m.venture_id===t.venture_id);
        const agent=baseAgent?{...baseAgent,...(membership?.overrides||{})}:null;
        if(agent?.provider&&agent?.model){
          const reroute=button('Resume with agent settings',()=>mutate('/api/tasks/'+encodeURIComponent(id)+'/resume',{agent_id:agent.id||agent.role,provider:agent.provider,model:agent.model,reasoning_effort:agent.reasoning_effort??null,astra_authorized:resumeAuthorization.checked},`Resume requested using ${agent.provider} / ${agent.model}.`));
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
  $('task-dialog').addEventListener('close',()=>{selectedTask=null;resumeAuthorization={task:null,checked:false};});
  const requestedView=new URLSearchParams(location.search).get('view');if(requestedView)showView(requestedView);
  refresh();
  setInterval(()=>{if(!document.hidden){refresh();refreshDetail();}},3000);
})();
