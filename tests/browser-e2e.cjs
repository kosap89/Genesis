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
  await page.locator('#objective').fill('Browser verification: missing credentials must block honestly.');
  await page.locator('#submit-objective').click();
  s=await waitState(18871,x=>x.tasks[0]?.status==='blocked_credentials');
  assert.equal(s.settings.spent_usd,0);assert.equal(s.settings.reserved_usd,0);
  await page.locator('#task-dialog [data-close]').click();
  await page.locator('[data-view=knowledge]').click();
  await page.locator('#memory-form [name=title]').fill('Persistent browser memory');
  await page.locator('#memory-form [name=content]').fill('This was saved through the real application.');
  await page.locator('#memory-form [type=submit]').click();
  await waitState(18871,x=>x.memories.length===1);
  await page.screenshot({path:path.join(output,'production-browser.png'),fullPage:true});
  await stop();await start(false,18871,path.join(temp,'real'));await page.reload();
  s=await waitState(18871,x=>x.memories.length===1&&x.tasks[0]?.status==='blocked_credentials');
  assert.equal(s.ventures[0].name,'Browser verified venture');
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
  await page.waitForTimeout(3200);await page.screenshot({path:path.join(output,'fixture-execution.png'),fullPage:true});
  assert.deepEqual(errors,[],'No JavaScript runtime errors');
  console.log('PASS: production browser venture/objective/credential-block/memory/restart/mobile; fixture browser approval, actual Python tests, artifact download. Live AI acceptance NOT verified.');
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();await stop();fs.rmSync(temp,{recursive:true,force:true});});
