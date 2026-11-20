// UI-only fixture; no real Skill is created or published.
const assert = require("node:assert/strict");
const base = process.env.BASE_URL || "http://127.0.0.1:5173";
const cdp = process.env.CDP_URL || "http://127.0.0.1:9367";

(async () => {
  const tab = await (await fetch(cdp+"/json/new?about:blank",{method:"PUT"})).json();
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
  let sequence=0;
  const pending=new Map();
  ws.onmessage=({data})=>{const m=JSON.parse(data);if(!m.id)return;const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);};
  const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
  const evaluate=async expression=>{const r=await send("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});assert(!r.exceptionDetails,JSON.stringify(r.exceptionDetails));return r.result.value;};
  const wait=async expression=>{for(let i=0;i<100;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,70));}throw Error("Timed out: "+expression);};
  try {
    await send("Page.enable");
    await send("Page.addScriptToEvaluateOnNewDocument",{source:`
      window.__rows=[
        {id:'none',name:'No version',published_version_number:null,latest_version_number:null,latest_version_status:null},
        {id:'draft',name:'Draft only',published_version_number:null,latest_version_number:1,latest_version_status:'draft'},
        {id:'published',name:'Published only',published_version_number:3,latest_version_number:3,latest_version_status:'published'},
        {id:'both',name:'Published plus draft',published_version_number:1,latest_version_number:2,latest_version_status:'draft'}
      ].map(s=>({...s,status:'active',is_global:true,description:''}));
      const originalFetch=window.fetch;
      window.fetch=async(url,options={})=>{
        const path=new URL(typeof url==='string'?url:url.url,location.href).pathname;
        const json=value=>Promise.resolve(new Response(JSON.stringify(value),{status:200,headers:{'Content-Type':'application/json'}}));
        if(path==='/v1/skills')return json(window.__rows);
        if(path==='/v1/skills/draft/versions')return json([{id:'draft-1',version_number:1,status:window.__rows[1].latest_version_status}]);
        if(path==='/v1/skills/draft/versions/draft-1/publish' && options.method==='POST'){
          window.__rows[1].published_version_number=1;window.__rows[1].latest_version_status='published';return json({});
        }
        if(path.startsWith('/v1/'))return json([]);
        return originalFetch(url,options);
      };
    `});
    await send("Page.navigate",{url:base+"/#skills"});
    await wait('document.querySelectorAll("tbody tr").length===4');
    const row=name=>`Array.from(document.querySelectorAll('tbody tr')).find(r=>r.querySelector('td strong')?.textContent.trim()===${JSON.stringify(name)})`;
    assert.match(await evaluate(`${row('No version')}.textContent`),/Chưa có version/);
    assert.match(await evaluate(`${row('Draft only')}.textContent`),/Chưa Publish.*Draft v1/s);
    assert.match(await evaluate(`${row('Published only')}.textContent`),/v3 · Published/);
    assert.match(await evaluate(`${row('Published plus draft')}.textContent`),/v1 · Published.*Draft v2/s);
    assert(await evaluate(`Array.from(document.querySelectorAll('thead th')).some(th=>th.textContent==='Version')`));
    await evaluate(`Array.from(${row('Draft only')}.querySelectorAll('button')).find(b=>b.textContent.trim()==='Versions').click()`);
    await wait(`Array.from(document.querySelectorAll('dialog[open] button')).some(b=>b.textContent.trim()==='Publish')`);
    await evaluate(`Array.from(document.querySelectorAll('dialog[open] button')).find(b=>b.textContent.trim()==='Publish').click()`);
    await wait('document.querySelectorAll("dialog[open]").length===2');
    await evaluate(`Array.from(document.querySelectorAll('dialog[open]')).at(-1).querySelector('.btn-danger').click()`);
    await wait(`${row('Draft only')}.textContent.includes('v1 · Published')`);
    assert(!(await evaluate(`${row('Draft only')}.textContent.includes('Draft v1')`)));
    console.log('PASS: Skill Version column: none, draft-only, published, newer draft; refreshes immediately after Publish. Mock API only.');
  } finally {await send('Page.close');ws.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
