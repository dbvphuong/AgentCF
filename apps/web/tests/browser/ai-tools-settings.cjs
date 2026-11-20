// CLI model Settings UI regression; isolated Server DB only: BASE_URL=http://127.0.0.1:5178 CDP_URL=http://127.0.0.1:9338.
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
    const before=await api("/v1/settings/models",undefined,"GET");
    const name="Favourite AGY "+Date.now().toString(36);
    await send("Runtime.enable");await send("Page.enable");
    await send("Page.navigate",{url:base+"/#settings"});
    await clickText("Công cụ AI trên PC");
    await wait(`!!document.querySelector('select[aria-label="Công cụ AI trên PC"]')`);
    await evaluate(`(()=>{const e=document.querySelector('select[aria-label="Công cụ AI trên PC"]');Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(e,'antigravity');e.dispatchEvent(new Event('change',{bubbles:true}))})()`);
    await clickText("+ Thêm mới");await fill("Tên hiển thị",name);await fill("Model ID gửi tới CLI","agy-favourite-"+name.split(" ").at(-1));await submit();
    await wait(`!document.querySelector('dialog[open]') && document.body.innerText.includes(${JSON.stringify(name)})`);
    let cli=(await api("/v1/settings/ai-tool-models",undefined,"GET")).find(m=>m.name===name);
    assert.equal(cli.tool_id,"antigravity");
    const edit=async()=>evaluate(`(()=>{const row=Array.from(document.querySelectorAll('tbody tr')).find(r=>r.innerText.includes(${JSON.stringify(name)}));Array.from(row.querySelectorAll('button')).find(b=>b.textContent.trim()==='Sửa').click()})()`);
    await edit();await wait('!!document.querySelector("dialog[open]")');await fill("Bật sử dụng","disabled");await fill("Model ID gửi tới CLI","agy-updated-"+name.split(" ").at(-1));await submit();
    await wait('!document.querySelector("dialog[open]")');
    cli=await api("/v1/settings/ai-tool-models/"+cli.id,undefined,"GET");assert.equal(cli.status,"disabled");assert.equal(cli.model_identifier,"agy-updated-"+name.split(" ").at(-1));
    assert(!(await api("/v1/settings/ai-tool-models?status=active",undefined,"GET")).some(m=>m.id===cli.id));
    await clickText("Providers & Models API");await clickText("Models API");
    await wait('document.body.innerText.includes("Test Model")');
    assert(!await evaluate(`document.body.innerText.includes(${JSON.stringify(name)})`));
    assert.deepEqual(await api("/v1/settings/models",undefined,"GET"),before);
    await send("Page.navigate",{url:base+"/#agents"});
    await wait('document.body.innerText.includes("Agent điều phối")');await clickText("+ Thêm mới");
    await wait('Array.from(document.querySelectorAll("dialog[open] label")).some(l=>l.textContent.startsWith("Model API"))');
    await wait('(()=>{const l=Array.from(document.querySelectorAll("dialog[open] label")).find(l=>l.textContent.startsWith("Model API"));return document.getElementById(l.htmlFor).options.length>1})()');
    const opts=await evaluate('(()=>{const l=Array.from(document.querySelectorAll("dialog[open] label")).find(l=>l.textContent.startsWith("Model API"));return Array.from(document.getElementById(l.htmlFor).options).map(o=>o.value)})()');
    assert(!opts.includes(cli.id));assert(before.some(m=>opts.includes(m.id)));await close();
    assert.equal(errors.length,0,JSON.stringify(errors));
    fs.mkdirSync(artifacts,{recursive:true});fs.writeFileSync(path.join(artifacts,"ai-tools-settings.json"),JSON.stringify({passed:true,checks:["CLI model created in selected tool","Edited exact ID and disabled model","API catalog unchanged","Agent selector contains only API models"],errors},null,2));
    console.log("Independent CLI Settings and API Agent model UI passed");
  }finally{ws.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
