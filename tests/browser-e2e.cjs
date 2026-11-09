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
async function waitState(port,predicate){for(let i=0;i<100;i++){const s=await(await fetch(`http://127.0.0.1:${port}/api/state`)).json();if(predicate(s))return s;await pause(150);}throw new Error('Expected state timed out');}
async function main(){
  const executable=process.env.GENESIS_BROWSER_PATH||['C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe','C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'].find(p=>fs.existsSync(p));
  browser=await chromium.launch({headless:true,...(executable?{executablePath:executable}:{})});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
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
  const engineering=page.locator('.agent-form[data-role=engineering]');
  const configureAgent=async(config)=>{
    await engineering.locator('[name=provider]').selectOption(config.provider);
    await engineering.locator('[name=model]').selectOption('__custom__');
    await engineering.locator('[name=custom_model]').fill(config.model);
    await engineering.locator('[name=reasoning_effort]').selectOption(config.reasoning_effort||'');
    await engineering.locator('[name=input_cost_per_million]').fill(String(config.input_cost_per_million));
    await engineering.locator('[name=output_cost_per_million]').fill(String(config.output_cost_per_million));
    await engineering.locator('[name=fallbacks]').fill(JSON.stringify(config.fallbacks));
    await engineering.locator('[type=submit]').click();
    await page.waitForFunction(()=>!document.querySelector('.agent-form[data-role=engineering] [type=submit]').disabled);
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
    const role=roles[i],form=page.locator('.agent-form[data-role="'+role+'"]');
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
    await page.waitForFunction(role=>!document.querySelector('.agent-form[data-role="'+role+'"] [type=submit]').disabled,role);
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
  for(const saved of savedModern){if(saved.role==='engineering')continue;const form=page.locator('.agent-form[data-role="'+saved.role+'"]');await form.locator('[name=provider]').selectOption(saved.before.provider);await form.locator('[name=model]').selectOption('__custom__');await form.locator('[name=custom_model]').fill(saved.before.model);await form.locator('[name=reasoning_effort]').selectOption(saved.before.reasoning_effort||'');await form.locator('[type=submit]').click();await waitState(18871,x=>x.agents.some(a=>a.role===saved.role&&a.model===saved.before.model));}
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
  await page.locator('#credentials-form [type=submit]').click();
  await page.locator('#feedback.error').filter({hasText:'API key must be printable'}).waitFor();
  assert.equal(await page.locator('#credentials-key').inputValue(),'');
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
  console.log('PASS: production browser venture/objective/credential-block/literal-XSS-safe-memory/opportunity/polling/settings/rates/fallback-save-restore/resume-route/session-credentials/restart/mobile/modern-model-catalog/reasoning-persistence/reporting-price-guard-separation/read-only-estimate/explicit-Astra-authorization; fixture browser approval, denial, actual Python tests, artifact and task ZIP downloads. Live AI acceptance NOT verified.');
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();await stop();fs.rmSync(temp,{recursive:true,force:true});});
