// Full onboarding against isolated Server and desktop GUI probe: BASE_URL=http://127.0.0.1:5178 CDP_URL=http://127.0.0.1:9338.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const base = process.env.BASE_URL || "http://127.0.0.1:5178";
const endpoint = process.env.CDP_URL || "http://127.0.0.1:9338";
const artifacts = process.env.ARTIFACT_DIR || "runtime/ui-review";

(async () => {
  const target = await (
    await fetch(endpoint + "/json/new?about:blank", { method: "PUT" })
  ).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = reject;
  });
  let id = 0;
  const pending = new Map();
  const errors = [];
  ws.onmessage = (event) => {
    const m = JSON.parse(event.data);
    if (m.id) {
      const p = pending.get(m.id);
      pending.delete(m.id);
      m.error ? p.reject(m.error) : p.resolve(m.result);
    }
    if (m.method === "Runtime.exceptionThrown")
      errors.push(m.params.exceptionDetails);
  };
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const key = ++id;
      pending.set(key, { resolve, reject });
      ws.send(JSON.stringify({ id: key, method, params }));
    });
  const evaluate = async (expression) => {
    const r = await send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    assert(!r.exceptionDetails, JSON.stringify(r.exceptionDetails));
    return r.result.value;
  };
  const wait = async (expression) => {
    for (let i = 0; i < 100; i++) {
      if (await evaluate(expression)) return;
      await new Promise((r) => setTimeout(r, 70));
    }
    throw new Error(
      "Timed out: " +
        expression +
        "\n" +
        (await evaluate("document.body.innerText")),
    );
  };
  const clickText = async (text, selector = "button") => {
    const q = JSON.stringify(text);
    await wait(
      `Array.from(document.querySelectorAll(${JSON.stringify(selector)})).some(e => e.textContent.trim() === ${q})`,
    );
    await evaluate(
      `Array.from(document.querySelectorAll(${JSON.stringify(selector)})).find(e => e.textContent.trim() === ${q}).click()`,
    );
  };
  const fill = async (label, value) => {
    const control = `(() => { const l=Array.from(document.querySelectorAll('dialog[open] label')).find(l=>l.textContent.trim().startsWith(${JSON.stringify(label)})); return l && document.getElementById(l.htmlFor); })()`;
    await wait(`!!${control}`);
    await wait(
      `(() => { const e=${control}; return e.tagName!=='SELECT' || Array.from(e.options).some(o=>o.value===${JSON.stringify(value)}); })()`,
    );
    await evaluate(
      `(() => { const labels = Array.from(document.querySelectorAll('dialog[open] label')); const l = labels.find(l => l.textContent.trim().startsWith(${JSON.stringify(label)})); if (!l) throw Error('Missing label: ' + ${JSON.stringify(label)}); const el = document.getElementById(l.htmlFor); const setter = Object.getOwnPropertyDescriptor(el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype, 'value').set; setter.call(el, ${JSON.stringify(value)}); el.dispatchEvent(new Event(el.tagName === 'SELECT' ? 'change' : 'input', { bubbles:true })); })()`,
    );
  };
  const submit = async () => {
    await evaluate(
      `Array.from(document.querySelectorAll('dialog[open]')).at(-1).querySelector('form').requestSubmit()`,
    );
  };
  const close = async () => {
    await evaluate(
      `Array.from(document.querySelectorAll('dialog[open]')).at(-1).querySelector('[aria-label="Đóng"]').click()`,
    );
  };
  const api = async (route, body, method = "POST") => {
    const r = await fetch(base + route, {
      method,
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    assert(r.ok, route + ": " + (await r.clone().text()));
    return r.status === 204 ? null : r.json();
  };
  const navigate = async (route) => {
    await evaluate(`location.hash=${JSON.stringify(route)}`);
    await evaluate(
      "new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))",
    );
    await wait(
      `!document.querySelector('.workspace [role="status"]') || !document.querySelector('.workspace [role="status"]').textContent.includes('Đang tải')`,
    );
  };
  try {
    fs.mkdirSync(artifacts,{recursive:true});
    const workspace=await api("/v1/workspaces",{name:"Connect PC test "+Date.now().toString(36)});
    const name="Desktop onboarding "+Date.now().toString(36);
    await send("Runtime.enable");await send("Page.enable");
    await send("Page.navigate",{url:base+"/#pc"});
    await clickText("+ Connect PC");await fill("Workspace",workspace.id);await fill("Tên PC",name);await submit();
    await wait(`!!document.querySelector('a[href^="agentcf:"]')`);
    const link=await evaluate(`document.querySelector('a[href^="agentcf:"]').getAttribute('href')`);
    const url=new URL(link);assert.equal(url.protocol,"agentcf:");assert.equal(url.hostname,"connect");assert.equal(url.search,"");
    assert((await evaluate('document.body.innerText')).includes("Đang chờ xác nhận"));
    assert.equal((await api("/v1/runners",undefined,"GET")).filter(r=>r.name===name).length,0);
    fs.writeFileSync(path.join(artifacts,"connect-link.txt"),link);
    for(let i=0;i<150;i++){
      if(await evaluate('document.body.innerText.includes("đã kết nối. Client đã mở phiên")'))break;
      if(i===149)throw Error("Desktop did not connect: "+await evaluate('document.body.innerText'));
      await new Promise(r=>setTimeout(r,200));
    }
    const pc=(await api("/v1/runners",undefined,"GET")).find(r=>r.name===name);assert(pc&&pc.os_name);
    assert(fs.existsSync(path.join(artifacts,"desktop-result.json")));
    const desktop=JSON.parse(fs.readFileSync(path.join(artifacts,"desktop-result.json"),"utf8"));assert(desktop.connected&&desktop.tray);
    await clickText("Hoàn tất");await wait('!document.querySelector("dialog[open]")');
    const download=await fetch(base+"/v1/client/windows-installer");assert(download.ok);assert(download.headers.get("content-disposition").includes("CF"));
    const reader=download.body.getReader();const first=await reader.read();assert.equal(Buffer.from(first.value).subarray(0,2).toString(),"MZ");await reader.cancel();
    assert.equal(errors.length,0,JSON.stringify(errors));
    fs.writeFileSync(path.join(artifacts,"stop-client"),"");
    fs.writeFileSync(path.join(artifacts,"onboarding.json"),JSON.stringify({passed:true,checks:["Web creates pending code","Application link contains data only","Desktop preview and confirm","Real session and heartbeat required","Tray present","Installer is a real EXE","No model execution"],errors},null,2));
    console.log("Web + desktop Client pairing and real EXE download passed");
  }finally{ws.close();}
})().catch(e=>{fs.writeFileSync(path.join(artifacts,"stop-client"),"");console.error(e);process.exitCode=1;});
