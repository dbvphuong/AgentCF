// Mock API only: PC actions placement, targeted reconnect and CPU/RAM freshness.
const assert=require('node:assert/strict');
const cdp=process.env.CDP_URL||'http://127.0.0.1:9367';
const base=process.env.BASE_URL||'http://127.0.0.1:5173';
(async()=>{
 const tab=await(await fetch(cdp+'/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(tab.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
 let n=0;const pending=new Map();ws.onmessage=({data})=>{const m=JSON.parse(data);if(!m.id)return;const p=pending.get(m.id);pending.delete(m.id);m.error?p.j(m.error):p.r(m.result);};
 const send=(method,params={})=>new Promise((r,j)=>{const id=++n;pending.set(id,{r,j});ws.send(JSON.stringify({id,method,params}));});
 const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});assert(!r.exceptionDetails,JSON.stringify(r.exceptionDetails));return r.result.value;};
 const wait=async expression=>{for(let i=0;i<100;i++){if(await ev(expression))return;await new Promise(r=>setTimeout(r,60));}throw Error('Timed out: '+expression);};
 const row=name=>`Array.from(document.querySelectorAll('tbody tr')).find(r=>r.querySelector('td button')?.textContent.trim()===${JSON.stringify(name)})`;
 try{
  await send('Page.enable');await send('Page.addScriptToEvaluateOnNewDocument',{source:`
   window.__rows=[{id:'a',workspace_id:'ws',name:'Online PC',status:'online',display_status:'online',cpu_percent:12.5,ram_percent:50,memory_used_bytes:8*1073741824,memory_total_bytes:16*1073741824},{id:'b',workspace_id:'ws',name:'Offline PC',status:'online',display_status:'offline',cpu_percent:99,ram_percent:99,memory_used_bytes:8*1073741824,memory_total_bytes:16*1073741824}];
   window.__pairPayload=null;window.__disconnected=false;
   const original=window.fetch;window.fetch=async(url,opt={})=>{const path=new URL(typeof url==='string'?url:url.url,location.href).pathname;const json=(v,status=200)=>Promise.resolve(new Response(status===204?null:JSON.stringify(v),{status,headers:{'Content-Type':'application/json'}}));
    if(path==='/v1/runners')return json(window.__rows);
    if(path==='/v1/workspaces')return json([{id:'ws',name:'Workspace'}]);
    if(path==='/v1/pairing-codes'&&opt.method==='POST'){window.__pairPayload=JSON.parse(opt.body);return json({id:'code',pairing_code:'a'.repeat(64),expires_at:'2099-01-01T00:00:00Z'});}
    if(path==='/v1/pairing-codes/code')return json({status:'pending'});
    if(path==='/v1/runners/a/disconnect'){window.__disconnected=true;window.__rows[0].display_status='offline';return json(null,204);}
    if(path.startsWith('/v1/'))return json([]);return original(url,opt);
   };
  `});
  await send('Page.navigate',{url:base+'/#pc'});await wait('document.querySelectorAll("tbody tr").length===2');
  assert(!(await ev(`${row('Offline PC')}.querySelector('td').textContent.includes('Kết nối')`)));
  assert(await ev(`${row('Offline PC')}.lastElementChild.textContent.includes('Kết nối')`));
  assert(await ev(`${row('Online PC')}.lastElementChild.textContent.includes('Hủy kết nối')`));
  assert.match(await ev(`${row('Online PC')}.textContent`),/12.5%/);
  assert.match(await ev(`${row('Online PC')}.textContent`),/8.0 \/ 16.0 GB/);
  assert(!(await ev(`${row('Offline PC')}.textContent.includes('99%')`)));
  await ev(`Array.from(${row('Offline PC')}.lastElementChild.querySelectorAll('button')).find(b=>b.textContent.trim()==='Kết nối').click()`);
  await wait('!!window.__pairPayload');assert.equal(await ev('window.__pairPayload.target_runner_id'),'b');
  await ev(`document.querySelector('dialog[open] [aria-label="Đóng"]').click()`);await wait('!document.querySelector("dialog[open]")');
  await ev(`Array.from(${row('Online PC')}.lastElementChild.querySelectorAll('button')).find(b=>b.textContent.trim()==='Hủy kết nối').click()`);
  await wait('!!document.querySelector("dialog[open]")');
  await ev(`Array.from(document.querySelectorAll('dialog[open] button')).find(b=>b.textContent.trim()==='Hủy kết nối').click()`);
  await wait('window.__disconnected && !document.querySelector("dialog[open]")');
  await wait(`${row('Online PC')}.lastElementChild.textContent.includes('Kết nối') && !${row('Online PC')}.lastElementChild.textContent.includes('Hủy kết nối')`);
  assert.equal(await ev('document.querySelectorAll("tbody tr").length'),2);
  console.log('PASS: actions column connect/disconnect, targeted PC ID, live CPU/RAM capacity, offline stale metrics hidden; mock API only.');
 }finally{await send('Page.close');ws.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
