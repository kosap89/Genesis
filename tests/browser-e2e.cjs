/* Real browser + HTTP + SQLite + Python execution. Model fixtures explicitly labelled. */
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const assert=require('node:assert/strict');

const source=path.resolve(__dirname,'..');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'genesis-browser-'));
const env={...process.env,PYTHONUNBUFFERED:'1'};
for(const key of ['GENESIS_OPENAI_API_KEY','OPENAI_API_KEY','GENESIS_ANTHROPIC_API_KEY','ANTHROPIC_API_KEY','GENESIS_GEMINI_API_KEY','GEMINI_API_KEY','GOOGLE_API_KEY'])delete env[key];
let processHandle,browser;
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function start(fixture,port,data){
  const args=fixture?['tests/browser_fixture.py','--port',String(port),'--data-dir',data]:['-m','genesis','--port',String(port),'--data-dir',data];
  processHandle=spawn('python',args,{cwd:source,env,windowsHide:true,stdio:['ignore','pipe','pipe']});
  let output='';processHandle.stdout.on('data',x=>output+=x);processHandle.stderr.on('data',x=>output+=x);
  for(let i=0;i<100;i++){
    if(processHandle.exitCode!==null)throw new Error('Server stopped: '+output);
    try{const r=await fetch(`http://127.0.0.1:${port}/api/health`);if(r.ok)return;}catch{}
    await pause(100);
  }
  throw new Error('Server startup timed out: '+output);
}
async function stop(){if(!processHandle)return;const p=processHandle;processHandle=null;await new Promise(resolve=>{if(p.exitCode!==null)return resolve();p.once('exit',resolve);p.kill();});}
async function waitState(port,predicate){for(let i=0;i<100;i++){const s=await(await fetch(`http://127.0.0.1:${port}/api/state`)).json();if(predicate(s))return s;await pause(150);}const last=await(await fetch(`http://127.0.0.1:${port}/api/state`)).json();throw new Error('Expected state timed out: '+JSON.stringify({tasks:last.tasks,agents:last.agents.map(a=>({id:a.id,name:a.name,model:a.model})),memberships:last.team_memberships,audit:last.audit.slice(-8)}));}
async function main(){
  const executable=process.env.GENESIS_BROWSER_PATH||['C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe','C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'].find(p=>fs.existsSync(p));
  browser=await chromium.launch({headless:true,...(executable?{executablePath:executable}:{})});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>{errors.push(e.message);console.error('Browser runtime error:',e.message);});
  const output=path.join(source,'test-results');fs.mkdirSync(output,{recursive:true});
  // Phase A: production service, credentials intentionally absent, no paid calls.
  await start(false,18871,path.join(temp,'real'));
  await page.goto('http://127.0.0.1:18871');
  await page.locator('#connection').filter({hasText:'Connected'}).waitFor();
  await page.locator('#new-venture').click();
  await page.locator('#venture-form [name=name]').fill('Browser verified venture');
  await page.locator('#venture-form [name=description]').fill('Real persistent browser interaction');
  await page.locator('#venture-form [type=submit]').click();
  let s=await waitState(18871,x=>x.ventures.length===1);
  await page.locator('#venture-select').selectOption(s.ventures[0].id);
  await page.locator('#objective-role').selectOption('engineering');
  await page.locator('#objective').fill('Browser verification: missing credentials must block honestly.');
  await page.locator('#submit-objective').click();
  s=await waitState(18871,x=>x.tasks[0]?.status==='blocked_credentials');
  assert.equal(s.settings.spent_usd,0);assert.equal(s.settings.reserved_usd,0);
  await page.locator('#task-dialog [data-close]').click();
  await page.locator('[data-view=knowledge]').click();
  await page.locator('#memory-form [name=title]').fill('Persistent browser memory');
  const unsafeMemory='<img src=x onerror="window.genesisXssExecuted=true"><script>window.genesisXssExecuted=true</script>\nThis must remain literal company knowledge.';
  await page.locator('#memory-form [name=content]').fill(unsafeMemory);
  await page.locator('#memory-form [type=submit]').click();
  s=await waitState(18871,x=>x.memories.length===1);
  await page.locator('#memory-list .record p').filter({hasText:'This must remain literal'}).waitFor();
  assert.equal(await page.locator('#memory-list .record p').textContent(),unsafeMemory,'Untrusted memory must render literally');
  assert.equal(await page.locator('#memory-list img, #memory-list script').count(),0,'Memory must not create markup');
  assert.equal(await page.evaluate(()=>Boolean(window.genesisXssExecuted)),false);
  // Polling must not erase a CEO's in-progress input.
  await page.locator('#memory-form [name=title]').fill('Unsubmitted draft');
  await page.waitForTimeout(3200);
  assert.equal(await page.locator('#memory-form [name=title]').inputValue(),'Unsubmitted draft');
  await page.locator('#opportunity-form [name=title]').fill('Browser verified opportunity');
  await page.locator('#opportunity-form [name=summary]').fill('An actual saved opportunity record; no demand claim.');
  await page.locator('#opportunity-form [type=submit]').click();
  await waitState(18871,x=>x.opportunities.length===1);
  // Configure real persisted controls without enabling broad execution permissions.
  const originalSettings={budget_usd:s.settings.budget_usd,max_steps:s.settings.max_steps,allow_network:s.settings.allow_network,allow_terminal:s.settings.allow_terminal};
  const originalAgent=s.agents.find(a=>a.role==='engineering');
  await page.locator('[data-view=settings]').click();
  await page.locator('#budget-usd').fill('8.25');
  await page.locator('#max-steps').fill('9');
  await page.locator('#settings-form [type=submit]').click();
  await waitState(18871,x=>x.settings.budget_usd===8.25&&x.settings.max_steps===9);
  const engineering=page.locator('.agent-form[data-agent-id=engineering]');
  const configureAgent=async(config)=>{
    await engineering.locator('[name=provider]').selectOption(config.provider);
    await engineering.locator('[name=model]').selectOption('__custom__');
    await engineering.locator('[name=custom_model]').fill(config.model);
    await engineering.locator('[name=reasoning_effort]').selectOption(config.reasoning_effort||'');
    await engineering.locator('[name=input_cost_per_million]').fill(String(config.input_cost_per_million));
    await engineering.locator('[name=output_cost_per_million]').fill(String(config.output_cost_per_million));
    await engineering.locator('[name=fallbacks]').fill(JSON.stringify(config.fallbacks));
    await engineering.locator('[type=submit]').click();
    await page.waitForFunction(()=>!document.querySelector('.agent-form[data-agent-id=engineering] [type=submit]').disabled);
  };
  const testAgent={provider:'gemini',model:'browser-configuration-only',input_cost_per_million:2.5,output_cost_per_million:7.5,fallbacks:[{provider:'anthropic',model:'browser-fallback-only'}]};
  await configureAgent(testAgent);
  await waitState(18871,x=>{const a=x.agents.find(a=>a.role==='engineering');return a.model===testAgent.model&&a.input_cost_per_million===2.5&&a.output_cost_per_million===7.5&&a.fallbacks[0]?.model==='browser-fallback-only';});
  // Catalog selections are configuration only; credentials are absent.
  const catalog=Object.fromEntries(s.providers.map(p=>[p.provider||p.id,p.model_catalog||[]]));
  assert(catalog.openai?.length,'OpenAI must publish a model catalog');
  for(const family of ['sol','terra','luna','astra'])assert(catalog.openai.some(m=>(m.label+' '+m.id).toLowerCase().includes(family)),family+' must be discoverable');
  const roles=['coo','engineering','strategy','qa'].filter(role=>s.agents.some(a=>a.role===role));
  const savedModern=[];
  for(let i=0;i<roles.length;i++){
    const role=roles[i],form=page.locator('.agent-form[data-agent-id="'+role+'"]');
    const model=catalog.openai.find(m=>(m.label+' '+m.id).toLowerCase().includes(['sol','terra','luna','astra'][i]));
    if(!model)continue;
    const before=s.agents.find(a=>a.role===role);
    await form.locator('[name=provider]').selectOption('openai');
    await form.locator('[name=model]').selectOption(model.id);
    const effort=model.reasoning_efforts?.includes('high')?'high':model.reasoning_efforts?.[0]||'';
    await form.locator('[name=reasoning_effort]').selectOption(effort);
    const [savedResponse]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/agents/'+role)&&r.request().method()==='POST'),form.locator('[type=submit]').click()]);
    const savedBody=await savedResponse.json();assert(savedResponse.ok(),role+' model configuration: '+JSON.stringify(savedBody));assert.equal(savedBody.model,model.id,role+' saved model');assert.equal(savedBody.reasoning_effort,effort||null,role+' saved effort');
    s=await waitState(18871,x=>x.agents.some(a=>a.role===role&&a.model===model.id&&a.reasoning_effort===(effort||null)));
    await page.waitForFunction(role=>!document.querySelector('.agent-form[data-agent-id="'+role+'"] [type=submit]').disabled,role);
    savedModern.push({role,model:model.id,effort,before});
  }
  assert((await page.locator('#accounting-summary').textContent()).includes('Official billed amount: unavailable'));
  const guardRates=s.agents.map(a=>[a.role,a.input_cost_per_million,a.output_cost_per_million]);
  await page.locator('#pricing-model').selectOption(catalog.openai[0].id);
  await page.locator('#pricing-input').fill('2.123');
  await page.locator('#pricing-form [type=submit]').click();
  await page.locator('#feedback').filter({hasText:'Reporting prices saved'}).waitFor();
  s=await waitState(18871,x=>x.providers.some(p=>(p.model_catalog||[]).some(m=>m.id===catalog.openai[0].id&&m.pricing.input_cost_per_million===2.123)));
  assert.deepEqual(s.agents.map(a=>[a.role,a.input_cost_per_million,a.output_cost_per_million]),guardRates,'Reporting overrides must leave enforcement rates unchanged');
  await page.locator('[data-view=overview]').click();
  const astra=savedModern.find(a=>a.model.includes('astra'));
  if(astra){
    await page.locator('#objective-role').selectOption(astra.role);
    await page.locator('#objective').fill('LOCAL PREVIEW ONLY: Astra requires explicit task authorization');
    assert.equal(await page.locator('#objective-astra').isChecked(),false);
    const before=s.tasks.length;
    const [rejected]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/tasks')&&r.request().method()==='POST'),page.locator('#submit-objective').click()]);
    assert(!rejected.ok(),'Astra task must be rejected without explicit authorization');
    s=await waitState(18871,x=>x.tasks.length===before);assert.equal(s.tasks.length,before);
    await page.locator('#objective-astra').check();
    await page.locator('#objective-estimate').filter({hasText:'Local preview only'}).waitFor();
  }
  await page.locator('#objective-role').selectOption(savedModern[0]?.role||'engineering');
  const count=s.tasks.length;
  await page.locator('#objective').fill('LOCAL PREVIEW ONLY: estimate without task creation');
  await page.locator('#objective-estimate').filter({hasText:/Local preview only|explicit|authorization/i}).waitFor();
  s=await waitState(18871,x=>x.tasks.length===count);assert.equal(s.tasks.length,count);
  await page.locator('#objective-astra').check();
  await page.locator('#objective-role').selectOption('engineering');
  if(savedModern[0]?.role!=='engineering')assert.equal(await page.locator('#objective-astra').isChecked(),false,'Role changes reset task-specific authorization');
  await page.locator('#objective').fill('');
  await page.screenshot({path:path.join(output,'production-browser.png'),fullPage:true});
  await stop();await start(false,18871,path.join(temp,'real'));await page.reload();
  s=await waitState(18871,x=>x.memories.length===1&&x.tasks[0]?.status==='blocked_credentials');
  assert.equal(s.ventures[0].name,'Browser verified venture');
  assert.equal(s.memories[0].content,unsafeMemory,'Literal memory must survive restart');
  assert.equal(s.opportunities[0].title,'Browser verified opportunity');
  assert.equal(s.settings.budget_usd,8.25);assert.equal(s.settings.max_steps,9);
  for(const saved of savedModern){const actual=s.agents.find(a=>a.role===saved.role);assert.equal(actual.model,saved.model);assert.equal(actual.reasoning_effort,saved.effort||null);}
  // Restore other role configurations; route the original blocked task using the custom test route.
  await page.locator('#connection').filter({hasText:'Connected'}).waitFor();
  await page.locator('[data-view=settings]').click();
  for(const saved of savedModern){if(saved.role==='engineering')continue;const form=page.locator('.agent-form[data-agent-id="'+saved.role+'"]');await form.locator('[name=provider]').selectOption(saved.before.provider);await form.locator('[name=model]').selectOption('__custom__');await form.locator('[name=custom_model]').fill(saved.before.model);await form.locator('[name=reasoning_effort]').selectOption(saved.before.reasoning_effort||'');await form.locator('[type=submit]').click();await waitState(18871,x=>x.agents.some(a=>a.role===saved.role&&a.model===saved.before.model));}
  await configureAgent(testAgent);
  await waitState(18871,x=>x.agents.find(a=>a.role==='engineering').model===testAgent.model);
  await page.locator('#connection').filter({hasText:'Connected'}).waitFor();
  await page.locator('[data-view=operations]').click();
  await page.locator('#all-tasks .record-title').first().click();
  // Await the mutation response before polling: an intermediate state may still
  // show the old blocked status while the new route and audit are being written.
  const [resumeResponse]=await Promise.all([
    page.waitForResponse(r=>r.url().endsWith('/api/tasks/'+s.tasks[0].id+'/resume')&&r.request().method()==='POST'),
    page.getByRole('button',{name:'Resume with agent settings',exact:true}).click(),
  ]);
  assert(resumeResponse.ok(),'Explicit resume request must succeed');
  s=await waitState(18871,x=>x.tasks[0]?.status==='blocked_credentials'&&x.tasks[0].provider===testAgent.provider&&x.tasks[0].model===testAgent.model&&x.audit.some(e=>e.action==='task_route_changed'&&e.task_id===x.tasks[0].id&&e.provider===testAgent.provider&&e.model===testAgent.model));
  assert(s.audit.some(e=>e.action==='task_route_changed'&&e.task_id===s.tasks[0].id&&e.provider===testAgent.provider&&e.model===testAgent.model),'Explicit resume route switch must be audited');
  assert.equal(s.settings.spent_usd,0,'Credential-blocked reroute must not charge usage');
  await page.locator('#task-dialog [data-close]').click();
  await page.locator('[data-view=settings]').click();
  assert.equal(await page.locator('#budget-usd').inputValue(),'8.25');
  assert.equal(await engineering.locator('[name=custom_model]').inputValue(),testAgent.model);
  await configureAgent(originalAgent);
  await waitState(18871,x=>x.agents.find(a=>a.role==='engineering').model===originalAgent.model);
  await page.locator('#budget-usd').fill(String(originalSettings.budget_usd));
  await page.locator('#max-steps').fill(String(originalSettings.max_steps));
  await page.locator('#settings-form [type=submit]').click();
  s=await waitState(18871,x=>x.settings.budget_usd===originalSettings.budget_usd&&x.settings.max_steps===originalSettings.max_steps);
  const restoredAgent=s.agents.find(a=>a.role==='engineering');
  for(const field of ['provider','model','input_cost_per_million','output_cost_per_million','fallbacks'])assert.deepEqual(restoredAgent[field],originalAgent[field],'Agent configuration restored: '+field);
  // No queued/running objectives remain: a test-only credential must never cause a paid call.
  assert(s.tasks.every(t=>!['queued','running'].includes(t.status)));
  const credential='browser-test-only-not-a-real-api-key';
  await page.locator('#credentials-provider').selectOption('gemini');
  assert.equal(await page.locator('#credentials-configure-agents').isChecked(),false,'Key entry must preserve existing agent routes by default');
  await page.locator('#credentials-configure-agents').uncheck();
  await page.locator('#credentials-key').fill(credential);
  await page.locator('#credentials-form [type=submit]').click();
  s=await waitState(18871,x=>x.providers.some(p=>p.provider==='gemini'&&p.configured));
  assert.equal(await page.locator('#credentials-key').inputValue(),'','Session key input must clear immediately');
  assert(!JSON.stringify(s).includes(credential),'Session credential must never appear in state or audit');
  assert(!(await page.locator('body').innerText()).includes(credential),'Credential must not be rendered');
  assert.equal(await page.evaluate(()=>JSON.stringify([Object.entries(localStorage),Object.entries(sessionStorage)]).includes('browser-test-only-not-a-real-api-key')),false);
  await page.locator('#credentials-clear').click();
  s=await waitState(18871,x=>x.providers.every(p=>p.provider!=='gemini'||!p.configured));
  // The clear handler also refreshes state and clears the input in finally.
  // Finish that handler before entering the next key.
  await page.waitForFunction(()=>!document.querySelector('#credentials-clear').disabled);
  assert.equal(s.settings.spent_usd,0);
  // A rejected request must clear the field as well.
  await page.locator('#credentials-key').fill('invalid whitespace key');
  const [invalidCredentialResponse]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/credentials')&&r.request().method()==='POST'),page.locator('#credentials-form [type=submit]').click()]);
  assert.equal(invalidCredentialResponse.status(),400,'Invalid credential validation: '+JSON.stringify(await invalidCredentialResponse.json()));
  await page.locator('#feedback.error').filter({hasText:'API key must be printable'}).waitFor();
  assert.equal(await page.locator('#credentials-key').inputValue(),'');
  // Dynamic team tests use only the isolated production server with no credentials.
  await page.locator('[data-view=team]').click();
  await page.locator('#venture-select').selectOption(s.ventures[0].id);
  await page.locator('#team-template').selectOption('engineering');
  await page.locator('#team-agent-name').fill('Frontend engineer');
  await page.locator('#team-specialization').fill('Frontend accessibility');
  await page.locator('#team-add-form [type=submit]').click();
  s=await waitState(18871,x=>x.agents.some(a=>a.name==='Frontend engineer'));
  const frontend=s.agents.find(a=>a.name==='Frontend engineer');
  assert.notEqual(frontend.id,'engineering');
  const memberForm=id=>page.locator('.team-agent-form[data-agent-id="'+id+'"]');
  await memberForm(frontend.id).getByRole('button',{name:'Duplicate agent',exact:true}).click();
  s=await waitState(18871,x=>x.agents.some(a=>a.name==='Frontend engineer copy'));
  const backend=s.agents.find(a=>a.name==='Frontend engineer copy');
  assert.notEqual(frontend.id,backend.id,'Same-role agents need separate identities');
  assert.equal(backend.role,frontend.role);
  const backendForm=memberForm(backend.id);
  await backendForm.locator('details').first().locator('summary').click();
  await backendForm.locator('[name=name]').fill('Backend engineer');
  await backendForm.locator('[name=specialization]').fill('API correctness');
  await backendForm.getByRole('button',{name:'Save global agent defaults',exact:true}).click();
  await waitState(18871,x=>x.agents.some(a=>a.id===backend.id&&a.name==='Backend engineer'));
  await backendForm.locator('[name=project_specialization]').fill('Venture-only API reviewer');
  await backendForm.locator('[name=project_system_instructions]').fill('Only in this venture: inspect API contracts.');
  await backendForm.locator('[name=responsibilities]').fill('Review API changes');
  await backendForm.locator('[name=use_override]').check();
  await backendForm.locator('[name=provider]').selectOption('openai');
  const teamModel=catalog.openai.find(m=>m.id.includes('sol'))||catalog.openai[0];
  await backendForm.locator('[name=model]').selectOption(teamModel.id);
  const teamEffort=teamModel.reasoning_efforts?.[0]||'';
  await backendForm.locator('[name=reasoning_effort]').selectOption(teamEffort);
  await backendForm.locator('[name=budget_usd]').fill('1.25');
  await backendForm.getByRole('button',{name:'Save global agent defaults',exact:true}).click();
  await waitState(18871,x=>x.agents.some(a=>a.id===backend.id&&a.budget_usd===1.25));
  await backendForm.locator('[name=project_specialization]').fill('Venture-only API reviewer');
  await backendForm.locator('[name=project_system_instructions]').fill('Only in this venture: inspect API contracts.');
  await backendForm.locator('[name=responsibilities]').fill('Review API changes');
  await backendForm.locator('[name=use_override]').check();
  await backendForm.locator('[name=provider]').selectOption('openai');
  await backendForm.locator('[name=model]').selectOption(teamModel.id);
  await backendForm.locator('[name=reasoning_effort]').selectOption(teamEffort);
  await backendForm.getByRole('button',{name:'Save project agent',exact:true}).click();
  s=await waitState(18871,x=>x.agents.some(a=>a.id===backend.id&&a.name==='Backend engineer'&&a.budget_usd===1.25)&&x.team_memberships.some(m=>m.agent_id===backend.id&&m.overrides?.model===teamModel.id));
  assert.equal(s.team_memberships.find(m=>m.agent_id===backend.id).responsibilities,'Review API changes');
  assert.equal(s.team_memberships.find(m=>m.agent_id===backend.id).system_instructions,'Only in this venture: inspect API contracts.');
  assert.notEqual(s.agents.find(a=>a.id===backend.id).system_instructions,'Only in this venture: inspect API contracts.','Venture instructions must not overwrite global defaults');
  await page.locator('#role-template-form [name=name]').fill('Accessibility specialist');
  await page.locator('#role-template-form [name=description]').fill('A custom reusable role');
  await page.locator('#role-template-form [name=system_instructions]').fill('Inspect accessibility and record verifiable findings.');
  await page.locator('#role-template-form [type=submit]').click();
  s=await waitState(18871,x=>x.role_templates.some(t=>t.name==='Accessibility specialist'));
  assert(s.role_templates.find(t=>t.name==='Accessibility specialist').system_instructions.includes('verifiable'));
  await page.waitForFunction(()=>!document.querySelector('#role-template-form [type=submit]').disabled);
  const savedTemplate=s.role_templates.find(t=>t.name==='Accessibility specialist');
  await page.locator('#role-template-edit').selectOption(savedTemplate.id);
  await page.locator('#role-template-model').selectOption(teamModel.id);
  await page.locator('#role-template-effort').selectOption(teamEffort);
  const [templateUpdate]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/role-templates/'+savedTemplate.id)&&r.request().method()==='POST'),page.locator('#role-template-form [type=submit]').click()]);
  assert(templateUpdate.ok(),'Template update: '+JSON.stringify(await templateUpdate.json()));
  s=await waitState(18871,x=>x.role_templates.some(t=>t.id===savedTemplate.id&&t.model===teamModel.id&&t.reasoning_effort===(teamEffort||null)));
  await page.locator('[data-view=overview]').click();
  await page.locator('#objective-role').selectOption(frontend.id);
  await page.locator('#objective').fill('Isolated team verification: missing credentials must block this specific frontend agent.');
  await page.locator('#submit-objective').click();
  s=await waitState(18871,x=>x.tasks.some(t=>t.agent_id===frontend.id&&t.status==='blocked_credentials'));
  const teamTask=s.tasks.find(t=>t.agent_id===frontend.id);
  assert.equal(teamTask.role,frontend.role);
  assert((await page.locator('#task-detail').innerText()).includes(frontend.id),'Task details must show exact agent identity');
  await page.locator('#task-dialog [data-close]').click();
  await page.locator('[data-view=team]').click();
  await memberForm(frontend.id).getByRole('button',{name:'Remove from project',exact:true}).click();
  s=await waitState(18871,x=>x.team_memberships.some(m=>m.agent_id===frontend.id&&m.status==='removed'));
  assert(s.tasks.some(t=>t.id===teamTask.id&&t.agent_id===frontend.id),'Removing membership preserves task identity and history');
  await page.locator('#new-venture').click();
  await page.locator('#venture-form [name=name]').fill('Isolated second project');
  await page.locator('#venture-form [name=description]').fill('Must not inherit the first project team');
  await page.locator('#venture-form [type=submit]').click();
  s=await waitState(18871,x=>x.ventures.length===2);
  const secondProject=s.ventures.find(v=>v.name==='Isolated second project');
  await memberForm(backend.id).locator('[name=project_specialization]').fill('Unsaved project draft');
  await page.locator('#venture-select').selectOption(secondProject.id);
  assert.equal(await page.locator('.team-agent-form').count(),0,'Project teams stay separate');
  assert.equal(await page.locator('#objective-role option[value="'+backend.id+'"]').count(),0,'Unassigned custom agents cannot be chosen for another project');
  await page.locator('#team-existing').selectOption(frontend.id);
  await page.locator('#team-assign-form [type=submit]').click();
  s=await waitState(18871,x=>x.team_memberships.some(m=>m.venture_id===secondProject.id&&m.agent_id===frontend.id&&m.status==='active'));
  await memberForm(frontend.id).waitFor();
  await page.locator('#project-budget').fill('0.75');
  await page.locator('#project-budget-form [type=submit]').click();
  s=await waitState(18871,x=>x.ventures.some(v=>v.id===secondProject.id&&v.budget_usd===0.75));
  await memberForm(frontend.id).locator('[name=enabled]').uncheck();
  await memberForm(frontend.id).getByRole('button',{name:'Save project agent',exact:true}).click();
  s=await waitState(18871,x=>x.team_memberships.some(m=>m.venture_id===secondProject.id&&m.agent_id===frontend.id&&m.enabled===false));
  await page.locator('#objective-role option[value="'+frontend.id+'"]').waitFor({state:'detached'});
  assert.equal(await page.locator('#objective-role option[value="'+frontend.id+'"]').count(),0,'Disabled membership cannot receive new objectives');
  await page.locator('[data-view=settings]').click();
  assert.equal(await page.locator('#max-concurrency').inputValue(),'1','Concurrency defaults to one');
  await page.locator('#max-concurrency').fill('2');
  await page.locator('#max-delegation-depth').fill('2');
  await page.locator('#max-delegated-tasks').fill('5');
  await page.locator('#settings-form [type=submit]').click();
  s=await waitState(18871,x=>x.settings.max_concurrency===2&&x.settings.max_delegation_depth===2&&x.settings.max_delegated_tasks===5);
  assert.equal(s.settings.spent_usd,0,'Dynamic team management and credential-blocked task must make no paid calls');

  // Durable venture documents use the real local persistence API; no model calls.
  await page.locator('[data-view=team]').click();
  await page.locator('#project-policy').fill('CEO approval required before proposing rule changes.');
  await page.locator('#project-policy-form [type=submit]').click();
  await waitState(18871,x=>x.ventures.find(v=>v.id===secondProject.id)?.operating_policy==='CEO approval required before proposing rule changes.');
  await page.locator('[data-view=documents]').click();
  await page.locator('#document-controls summary').click();
  await page.locator('#document-create-form [name=name]').fill('Approved source reference.md');
  const sourceText='# Source reference\n<img src=x onerror="window.genesisDocXss=true">\nCEO supplied content.';
  await page.locator('#document-create-form [name=content]').fill(sourceText);
  const [documentCreated]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/projects/'+secondProject.id+'/documents')&&r.request().method()==='POST'),page.locator('#document-create-form [type=submit]').click()]);
  assert(documentCreated.ok(),'Document create: '+JSON.stringify(await documentCreated.json()));
  s=await waitState(18871,x=>x.venture_documents.some(d=>d.name==='Approved source reference.md'));
  const reference=s.venture_documents.find(d=>d.name==='Approved source reference.md');
  await page.locator('#document-content').waitFor({state:'visible'});
  assert.equal(await page.locator('#document-content').inputValue(),sourceText);
  assert.equal(await page.evaluate(()=>Boolean(window.genesisDocXss)),false);
  await page.locator('#document-content').fill(sourceText+'\nCEO corrected reference.');
  await page.locator('#document-revise-form [type=submit]').click();
  await waitState(18871,x=>x.venture_documents.find(d=>d.id===reference.id)?.revision===2);
  await page.locator('#document-history summary').filter({hasText:'Revision 1'}).waitFor();
  const [referenceDownload]=await Promise.all([page.waitForEvent('download'),page.locator('#document-download').click()]);
  assert((fs.readFileSync(await referenceDownload.path(),'utf8')).includes('CEO corrected reference.'));
  await stop();await start(false,18871,path.join(temp,'real'));
  await page.goto('http://127.0.0.1:18871/?venture='+encodeURIComponent(secondProject.id)+'&view=documents');
  await page.locator('#document-list button').filter({hasText:'Approved source reference.md'}).click();
  await page.locator('#document-content').waitFor({state:'visible'});
  assert.equal(await page.locator('#venture-select').inputValue(),secondProject.id,'Venture deep link restores selected project');
  assert.equal(await page.locator('#document-content').inputValue(),sourceText+'\nCEO corrected reference.','Document revisions survive restart');
  await page.locator('#document-history summary').filter({hasText:'Revision 1'}).waitFor();
  s=await waitState(18871,x=>x.ventures.find(v=>v.id===secondProject.id)?.operating_policy==='CEO approval required before proposing rule changes.');
  await page.locator('#venture-select').selectOption(s.ventures.find(v=>v.id!==secondProject.id).id);
  assert.equal(await page.locator('#document-list [data-document-id="'+reference.id+'"]').count(),0,'Documents remain isolated by venture');

  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(output,'mobile-browser.png'),fullPage:true});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth),false,'Mobile should not overflow horizontally');
  await stop();
  // Phase B: test-only model double, actual files/tests/approvals through the UI.
  await start(true,18872,path.join(temp,'fixture'));await page.setViewportSize({width:1440,height:1000});await page.goto('http://127.0.0.1:18872');
  await page.locator('#connection').filter({hasText:'Connected'}).waitFor();
  await page.locator('#objective-role').selectOption('engineering');
  await page.locator('#objective').fill('BROWSER TEST FIXTURE ONLY: create calculator and run its tests.');
  await page.locator('#submit-objective').click();
  s=await waitState(18872,x=>x.tasks[0]?.status==='waiting_approval');
  assert.equal(s.approvals.length,1);
  await page.locator('#task-dialog [data-close]').click();
  await page.getByRole('button',{name:'Approve action',exact:true}).first().click();
  s=await waitState(18872,x=>x.tasks[0]?.status==='completed');
  const detail=await(await fetch('http://127.0.0.1:18872/api/tasks/'+s.tasks[0].id)).json();
  const tool=detail.messages.find(m=>m.role==='tool'&&m.name==='run_python_tests');
  assert(tool,'Real test tool result must exist');assert.equal(JSON.parse(tool.content).returncode,0);
  assert(JSON.parse(tool.content).output.includes('Ran 1 test'),'The test runner must actually discover a test');
  assert(s.artifacts.some(a=>a.name==='calculator.py'));
  const artifact=s.artifacts.find(a=>a.name==='calculator.py');
  const download=await(await fetch('http://127.0.0.1:18872/api/artifacts/'+artifact.id)).text();assert(download.includes('return a + b'));
  await page.locator('[data-view=operations]').click();
  await page.locator('#all-tasks .record-title').first().click();
  const [bundleDownload]=await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('link',{name:'Download task ZIP',exact:true}).click(),
  ]);
  assert(bundleDownload.suggestedFilename().startsWith('genesis-'));
  assert.equal(await bundleDownload.failure(),null);
  assert.equal(fs.readFileSync(await bundleDownload.path()).subarray(0,4).toString('hex'),'504b0304','Task ZIP UI must download a nonempty ZIP archive');
  await page.locator('#task-dialog [data-close]').click();
  await page.waitForTimeout(3200);await page.screenshot({path:path.join(output,'fixture-execution.png'),fullPage:true});
  // A separate denied invocation must produce a refusal tool record, never execute tests.
  await page.locator('[data-view=overview]').click();
  await page.locator('#objective').fill('BROWSER TEST FIXTURE ONLY: verify CEO denial prevents test execution.');
  await page.locator('#submit-objective').click();
  s=await waitState(18872,x=>x.tasks.length===2&&x.tasks[1].status==='waiting_approval');
  const deniedTask=s.tasks[1];
  await page.locator('#task-dialog [data-close]').click();
  await page.getByRole('button',{name:'Deny',exact:true}).first().click();
  s=await waitState(18872,x=>x.tasks.find(t=>t.id===deniedTask.id)?.status==='completed');
  const deniedDetail=await(await fetch('http://127.0.0.1:18872/api/tasks/'+deniedTask.id)).json();
  const deniedTool=deniedDetail.messages.find(m=>m.role==='tool'&&m.name==='run_python_tests');
  assert(deniedTool,'Denied tool must have an explicit recorded result');
  assert(JSON.parse(deniedTool.content).error.includes('CEO denied'));
  assert.equal(JSON.parse(deniedTool.content).returncode,undefined,'Denied invocation must not have a process result');
  assert.equal(s.approvals.find(a=>a.task_id===deniedTask.id).status,'denied');
  assert.deepEqual(errors,[],'No JavaScript runtime errors');
  console.log('PASS: production browser venture/objective/credential-block/literal-XSS-safe-memory/opportunity/polling/settings/rates/fallback-save-restore/resume-route/session-credentials/restart/mobile/modern-model-catalog/reasoning-persistence/reporting-price-guard-separation/read-only-estimate/explicit-Astra-authorization/dynamic-teams/venture-instructions/global-default-isolation/operating-policy/durable-document-revisions/download/restart/deep-links/duplicate-identities/project-isolation/project-overrides/membership-disable-remove-reassign/template-edit/history/concurrency-controls/unsaved-draft-project-switch; fixture browser approval, denial, actual Python tests, artifact and task ZIP downloads. Live AI acceptance NOT verified.');
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();await stop();fs.rmSync(temp,{recursive:true,force:true});});
