// Node task form regression; isolated Server DB only: BASE_URL=http://127.0.0.1:5178 CDP_URL=http://127.0.0.1:9338.
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
    const suffix=Date.now().toString(36);
    const wsData=await api("/v1/workspaces",{name:"Node test "+suffix});
    const provider=await api("/v1/settings/providers",{id:"p-"+suffix,name:"Local "+suffix,api_format:"custom",base_url:"http://127.0.0.1"});
    const codex=await api("/v1/settings/ai-tool-models",{id:"codex-"+suffix,name:"Codex model "+suffix,tool_id:"codex",model_identifier:"codex-exact"});
    const agy=await api("/v1/settings/ai-tool-models",{id:"agy-"+suffix,name:"Agy model "+suffix,tool_id:"antigravity",model_identifier:"agy-exact"});
    const apiModel=await api("/v1/settings/models",{id:"api-"+suffix,name:"Controller API "+suffix,provider_id:provider.id,model_identifier:"api-controller-only"});
    const role=await api("/v1/settings/roles",{id:"role-"+suffix,name:"Writer "+suffix});
    const code=await api("/v1/pairing-codes",{workspace_id:wsData.id,name:"Node PC "+suffix});
    const pc=await api("/v1/runners/pair",{pairing_code:code.pairing_code});
    const skill=await api("/v1/skills",{id:"skill-"+suffix,name:"Local Skill "+suffix,is_global:true,source_path:"C:\\NodeTest\\main.md",source_runner_id:pc.runner_id});
    const version=(await api("/v1/skills/"+skill.id+"/versions",undefined,"GET"))[0];
    await api("/v1/skills/"+skill.id+"/versions/"+version.id+"/publish",{});
    const pm=await api("/v1/agents",{id:"pm-"+suffix,name:"PM "+suffix,role_id:role.id,model_id:apiModel.id,skill_ids:[skill.id]});
    const worker=await api("/v1/agents",{id:"worker-"+suffix,name:"Writer "+suffix,role_id:role.id,model_id:apiModel.id,skill_ids:[skill.id]});
    const project=await api("/v1/projects",{workspace_id:wsData.id,name:"Node Project "+suffix,pm_agent_id:pm.id});
    const process=await api("/v1/projects/"+project.id+"/processes",{name:"Node Process "+suffix});
    await send("Runtime.enable");await send("Page.enable");
    await send("Page.navigate",{url:base+"/#projects/"+project.id+"/processes/"+process.id});
    await clickText("+ Bước AI / Skill");
    await wait('document.body.innerText.includes("Nhiệm vụ")');
    assert.equal(await evaluate('Array.from(document.querySelectorAll("dialog[open] label")).some(e=>e.textContent.includes("Task key"))'),false);
    assert.equal(await evaluate('document.querySelector("dialog[open] .advanced-settings").open'),false);
    await fill("Tên bước","Tạo nội dung");
    assert.equal(await evaluate('document.querySelector("dialog[open]").textContent.includes("Quản lý Team")'),false);
    await fill("Agent điều phối",worker.id);
    const fieldValue=label=>evaluate(`(()=>{const l=Array.from(document.querySelectorAll('dialog[open] label')).find(e=>e.textContent.startsWith(${JSON.stringify(label)}));return document.getElementById(l.htmlFor).value})()`);
    assert.equal(await fieldValue("Model thực thi"),"");
    await fill("Model thực thi",codex.id);
    await fill("Skill",skill.id);
    assert.equal(await fieldValue("PC thực thi"),pc.runner_id);
    await fill("Công cụ AI thực thi","antigravity");
    assert.equal(await fieldValue("Model thực thi"),"");
    const modelOptions=await evaluate('(()=>{const l=Array.from(document.querySelectorAll("dialog[open] label")).find(e=>e.textContent.startsWith("Model thực thi"));return Array.from(document.getElementById(l.htmlFor).options).map(o=>o.value)})()');
    assert(modelOptions.includes(agy.id)&&!modelOptions.includes(codex.id)&&!modelOptions.includes(apiModel.id));
    await fill("Model thực thi",agy.id);await fill("Nhiệm vụ","done");await fill("Thư mục làm việc trên PC","C:\\NodeTest\\output");
    await submit();await wait('!document.querySelector("dialog[open]")');
    await clickText("Lưu draft");await wait('document.body.innerText.includes("Đã lưu draft.")');
    await clickText("Validate");await wait('document.body.innerText.includes("Cấu hình hợp lệ")');
    await clickText("Publish");await clickText("Xác nhận","dialog[open] button");
    await wait('!document.querySelector("dialog[open]")');
    const published=(await api("/v1/processes/"+process.id,undefined,"GET")).versions.find(v=>v.status==="published");
    assert(published,"Node must publish successfully");const node=published.definition.tasks[0];
    assert.equal(node.instructions,"done");assert.equal(node.runtime.model_id,"agy-exact");assert.equal(node.runtime.tool_model_id,agy.id);assert.equal(node.agent_id,worker.id);assert(node.task_key.startsWith("task_"));
    assert.equal((await api("/v1/agents/"+worker.id,undefined,"GET")).model_id,apiModel.id);
    await clickText("Tạo / mở draft");await wait('document.body.innerText.includes("Lưu draft")');
    await evaluate('document.querySelector(".graph-node:not(.start-node)").click()');
    await clickText("Sửa node");await wait('!!document.querySelector("dialog[open]")');
    assert.equal(await fieldValue("Model thực thi"),agy.id);assert.equal(await fieldValue("Nhiệm vụ"),"done");
    await clickText("Cấu hình nâng cao","summary");await fill("Timeout (giây)","900");
    await submit();await wait('!document.querySelector("dialog[open]")');
    await clickText("Lưu draft");await wait('document.body.innerText.includes("Đã lưu draft.")');
    const after=(await api("/v1/processes/"+process.id,undefined,"GET")).versions;
    const draft=after.find(v=>v.status==="draft").definition.tasks[0];
    assert.equal(draft.task_key,node.task_key);assert.equal(draft.execution_timeout_seconds,900);
    assert.equal(draft.runtime.model_id,"agy-exact");
    assert.deepEqual(after.find(v=>v.status==="published"),published);
    assert.equal(errors.length,0,JSON.stringify(errors));
    fs.mkdirSync(artifacts,{recursive:true});fs.writeFileSync(path.join(artifacts,"node-task.json"),JSON.stringify({passed:true,node,errors},null,2));
    console.log("Node form direct Agent selection/model/task/PC defaults and publication passed");
  }finally{ws.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
