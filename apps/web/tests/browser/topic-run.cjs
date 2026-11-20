// Browser fixture for topic launch and input/scroll responsiveness. No real Run/model.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.BASE_URL||'http://127.0.0.1:5173';
const cdp=process.env.CDP_URL||'http://127.0.0.1:9367';
(async()=>{
 const tab=await(await fetch(cdp+'/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(tab.webSocketDebuggerUrl);
 await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
 let id=0;const pending=new Map();
 ws.onmessage=({data})=>{const m=JSON.parse(data);if(!m.id)return;const p=pending.get(m.id);pending.delete(m.id);m.error?p.j(m.error):p.r(m.result);};
 const send=(method,params={})=>new Promise((r,j)=>{const key=++id;pending.set(key,{r,j});ws.send(JSON.stringify({id:key,method,params}));});
 const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});assert(!r.exceptionDetails,JSON.stringify(r.exceptionDetails));return r.result.value;};
 const wait=async condition=>{for(let i=0;i<120;i++){if(await ev(condition))return;await new Promise(r=>setTimeout(r,50));}throw Error('Timed out: '+condition+'\n'+await ev('document.body.innerText'));};
 const click=async text=>{await wait(`Array.from(document.querySelectorAll('button')).some(e=>e.textContent.trim()===${JSON.stringify(text)})`);await ev(`Array.from(document.querySelectorAll('button')).find(e=>e.textContent.trim()===${JSON.stringify(text)}).click()`);};
 const fill=async(selector,value)=>ev(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});Object.getOwnPropertyDescriptor(e.tagName==='SELECT'?HTMLSelectElement.prototype:e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event(e.tagName==='SELECT'?'change':'input',{bubbles:true}));})()`);
 try{
  await send('Page.enable');
  await send('Page.addScriptToEvaluateOnNewDocument',{source:`
   window.__runRequests=[];window.__requests=0;window.__browsePath='E:\\\\Project';window.__fixtureTopic='E:\\\\Project\\\\Topic 2';
   const original=window.fetch;
   window.fetch=async(url,opt={})=>{
    const path=new URL(typeof url==='string'?url:url.url,location.href).pathname;
    const json=x=>Promise.resolve(new Response(JSON.stringify(x),{status:200,headers:{'Content-Type':'application/json'}}));
    if(path.startsWith('/v1/'))window.__requests++;
    if(path==='/v1/projects')return json([{id:'p',name:'Project',status:'active'}]);
    if(path==='/v1/projects/p')return json({id:'p',processes:[{id:'proc',name:'Process',status:'active'}]});
    if(path==='/v1/processes/proc')return json({id:'proc',versions:[{id:'version',version_number:1,status:'published'}]});
    if(path.endsWith('/run-context'))return json({topic_supported:true,working_directory:'E:\\\\Project',runner_id:'pc',process_name:'Process'});
    if(path==='/v1/runners')return json([{id:'pc',name:'Local PC',status:'online',display_status:window.__offline?'offline':'online'}]);
    if(path==='/v1/runners/pc/skill-files'&&opt.method==='POST'){window.__browsePath=JSON.parse(opt.body).path;return json({id:'browse'});}
    if(path==='/v1/runners/pc/skill-files/browse')return json({status:'completed',result:{path:window.__browsePath,parent:'E:\\\\Project',roots:[],entries:[{name:'Topic 2',path:window.__fixtureTopic,is_dir:true},{name:'SKILL.md',path:'E:\\\\Project\\\\SKILL.md',is_dir:false},...Array.from({length:150},(_,i)=>({name:'Folder '+i,path:'E:\\\\Project\\\\Folder '+i,is_dir:true}))]}});
    if(path==='/v1/runs'&&opt.method==='POST'){window.__runRequests.push(JSON.parse(opt.body));return json({id:'fixture-run'});}
    if(path==='/v1/runs/fixture-run')return json({id:'fixture-run',process_id:'proc',process_version_id:'version',status:'queued',input:{topic:'Topic 2'},task_runs:[]});
    if(path==='/v1/runs/fixture-run/events')return json({items:[]});
    if(path.startsWith('/v1/'))return json([]);
    return original(url,opt);
   };
  `});
  await send('Page.navigate',{url:base+'/#runs/new'});
  await wait('!!document.querySelector("#run-project option[value=p]")');await fill('#run-project','p');
  await wait('!!document.querySelector("#run-process option[value=proc]")');await fill('#run-process','proc');
  await wait('!!document.querySelector("#run-version option[value=version]")');await fill('#run-version','version');
  await wait('!!document.querySelector("#run-topic")');
  assert(!(await ev('!!document.querySelector("#run-input")')));
  await click('Chạy Process');
  await wait('document.body.innerText.includes("Chọn hoặc nhập đường dẫn")');
  assert.equal(await ev('window.__runRequests.length'),0);
  await click('Chọn thư mục…');
  await wait('!!document.querySelector("dialog[open]") && document.querySelector("dialog[open]").textContent.includes("Topic 2")');
  assert(!(await ev('document.querySelector("dialog[open]").textContent.includes("SKILL.md")')));
  const hasVideo = await ev('document.querySelector(".brand-video, .brand-logo")?.tagName === "VIDEO"');
  if (hasVideo) {
    assert(await ev('document.querySelector(".brand-video").paused'),'Background video pauses while a modal is open');
  }
  assert.equal(await ev('getComputedStyle(document.querySelector("dialog"),"::backdrop").backdropFilter'),'none');
  await ev(`(()=>{window.__latencies=[];const e=document.querySelector('dialog input');e.focus();e.addEventListener('input',()=>{const start=performance.now();requestAnimationFrame(()=>window.__latencies.push(performance.now()-start));},{capture:true});})()`);
  const requests=await ev('window.__requests');
  for(const letter of ' typing performance check')await send('Input.insertText',{text:letter});
  await ev('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');
  assert.equal(await ev('window.__requests'),requests,'Typing does not issue API calls');
  const typing=await ev('window.__latencies');assert(typing.length>10);
  const scroll=await ev(`new Promise(resolve=>{const box=document.querySelector('dialog div[style*="overflow"]');const gaps=[];let previous=performance.now();let count=0;function frame(now){gaps.push(now-previous);previous=now;box.scrollTop+=12;if(++count<30)requestAnimationFrame(frame);else resolve(gaps);}requestAnimationFrame(frame);})`);
  assert(Math.max(...typing)<500,'Typing must not stall for half a second');
  await click('📁 Topic 2');
  await wait('document.querySelector("dialog code")?.textContent===window.__fixtureTopic');
  await click('Dùng thư mục này');
  await wait('!document.querySelector("dialog[open]")');
  if (hasVideo) {
    await wait('document.hidden || !document.querySelector(".brand-video").paused');
  }
  assert.equal(await ev('document.querySelector("#run-topic").value'),await ev('window.__fixtureTopic'));
  const pasted=await ev('window.__fixtureTopic');await fill('#run-topic',pasted);await fill('#run-request','Giữ phong cách theo Skill.');
  await click('Chạy Process');await wait('window.__runRequests.length===1');
  const payload=await ev('window.__runRequests[0]');
  assert.equal(payload.process_version_id,'version');assert.equal(payload.input.topic_directory,pasted);assert.equal(payload.input.request,'Giữ phong cách theo Skill.');
  assert.equal(payload.input.working_directory,undefined);
  await ev('window.__offline=true;location.hash="runs/new"');
  await wait('!!document.querySelector("#run-project option[value=p]")');await fill('#run-project','p');
  await wait('!!document.querySelector("#run-process option[value=proc]")');await fill('#run-process','proc');
  await wait('!!document.querySelector("#run-version option[value=version]")');await fill('#run-version','version');
  await wait('!!document.querySelector("#run-topic") && document.body.innerText.includes("PC chưa online")');
  assert(await ev(`Array.from(document.querySelectorAll('button')).find(e=>e.textContent.trim()==='Chọn thư mục…').disabled`));
  await fill('#run-topic',pasted);
  assert.equal(await ev('document.querySelector("#run-topic").value'),pasted);
  const report={passed:true,typing_samples:typing.length,typing_p95_ms:[...typing].sort((a,b)=>a-b)[Math.floor(typing.length*.95)],scroll_max_frame_ms:Math.max(...scroll),modal_video_paused:true,background_blur:false};
  fs.mkdirSync('runtime/topic-ui-check',{recursive:true});fs.writeFileSync('runtime/topic-ui-check/browser.json',JSON.stringify(report,null,2));
  console.log(JSON.stringify(report));
 }finally{await send('Page.close');ws.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
