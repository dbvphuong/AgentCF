// Requires isolated Server DB and heartbeat-only Client; see SKL-005: BASE_URL=http://127.0.0.1:5178 CDP_URL=http://127.0.0.1:9338.
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
    const fixture=JSON.parse(fs.readFileSync(process.env.SKILL_FILE_FIXTURE || "runtime/skill-file-ui/state.json","utf8"));
    await send("Runtime.enable"); await send("Page.enable");
    await send("Page.navigate",{url:base+"/#skills"});
    await wait('document.body.innerText.includes("+ Thêm mới")');
    await clickText("+ Thêm mới");
    await fill("Tên", "Skill file UI");
    await fill("PC chứa file Skill", fixture.runner_id);
    await fill("File .md chính của Skill", fixture.directory);
    await evaluate('Array.from(document.querySelectorAll("dialog[open] label")).find(e=>e.textContent.includes("Global (tất cả Project)")).querySelector("input").click()');
    await clickText("Chọn file…");
    await wait('document.querySelectorAll("dialog[open]").length===2 && Array.from(document.querySelectorAll("button")).some(e=>e.textContent.includes("main.md"))');
    await clickText("📄 main.md");
    await wait('document.querySelectorAll("dialog[open]").length===1');
    await submit();
    await wait('!document.querySelector("dialog[open]") && document.body.innerText.includes("Skill file UI")');
    const skill=(await api("/v1/skills",undefined,"GET")).find(s=>s.name==="Skill file UI");
    assert.equal(skill.source_path,fixture.file);
    assert.equal(skill.source_runner_id,fixture.runner_id);
    assert.equal((await api("/v1/skills/"+skill.id+"/versions",undefined,"GET")).length,1);
    await clickText("Sửa","tbody button");
    await wait('!!document.querySelector("dialog[open]")');
    assert.equal(await evaluate('Array.from(document.querySelectorAll("dialog[open] label")).filter(l=>l.textContent.startsWith("File .md chính" )).map(l=>document.getElementById(l.htmlFor).value)[0]'),fixture.file);
    await fill("File .md chính của Skill",fixture.file.replace("main.md","second.md"));
    await submit(); await wait('!document.querySelector("dialog[open]")');
    assert.equal((await api("/v1/skills/"+skill.id,undefined,"GET")).source_path,fixture.file.replace("main.md","second.md"));
    assert.equal(errors.length,0,JSON.stringify(errors));
    fs.mkdirSync(artifacts,{recursive:true});
    fs.writeFileSync(path.join(artifacts,"skill-file-ui.json"),JSON.stringify({passed:true,checks:["Create form has source PC/path/chooser","Real Client directory browse","Select main.md","Save original absolute path","Edit paste path"],errors},null,2));
    console.log("Skill file create/edit and real Client chooser passed");
  } finally { ws.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
