// Read-only UI regression. The Run POST is intercepted before it reaches Server.
// Requires populated local catalog/history; never creates a Run or calls a model.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const base = process.env.BASE_URL || "http://127.0.0.1:5173";
const cdp = process.env.CDP_URL || "http://127.0.0.1:9348";
const dir = process.env.ARTIFACT_DIR || "runtime/visible-identifiers";

(async () => {
  fs.mkdirSync(dir, { recursive: true });
  const get = async path => {
    const response = await fetch(base + path);
    assert(response.ok, path);
    return response.json();
  };
  const [skills, projects, history, models, agents, roles, runners] = await Promise.all([
    get("/v1/skills"), get("/v1/projects"), get("/v1/runs"), get("/v1/settings/models"),
    get("/v1/agents"), get("/v1/settings/roles"), get("/v1/runners"),
  ]);
  assert(skills.length && history.items.length, "Needs existing Skill and Run data; no test data is seeded.");
  let source;
  for (const project of projects.filter(p => p.status === "active")) {
    const detail = await get("/v1/projects/" + project.id);
    for (const process of detail.processes.filter(p => p.status === "active")) {
      const config = await get("/v1/processes/" + process.id);
      const version = config.versions.find(v => v.status === "published");
      if (version) { source = { project, process, version }; break; }
    }
    if (source) break;
  }
  assert(source, "Needs an existing published Process.");
  const target = await (await fetch(cdp + "/json/new?about:blank", { method: "PUT" })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  let seq = 0;
  const pending = new Map(), errors = [];
  let submitted;
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++seq; pending.set(id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params }));
  });
  ws.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const p = pending.get(message.id); pending.delete(message.id);
      message.error ? p.reject(message.error) : p.resolve(message.result);
    }
    if (message.method === "Runtime.exceptionThrown") errors.push(message.params);
    if (message.method === "Fetch.requestPaused") {
      const { requestId, request } = message.params;
      if (request.method === "POST") {
        submitted = JSON.parse(request.postData);
        // Never forward the model-triggering mutation to the local Server.
        send("Fetch.fulfillRequest", { requestId, responseCode: 422,
          responseHeaders: [{ name: "Content-Type", value: "application/json" }],
          body: Buffer.from(JSON.stringify({ detail: "UI test: Run not created" })).toString("base64"),
        }).catch(error => errors.push(error));
      } else send("Fetch.continueRequest", { requestId }).catch(error => errors.push(error));
    }
  };
  const evaluate = async expression => {
    const result = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    assert(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const wait = async expression => {
    for (let i = 0; i < 150; i++) {
      if (await evaluate(expression)) return;
      await new Promise(resolve => setTimeout(resolve, 60));
    }
    throw Error("Timeout: " + expression + "\n" + await evaluate("document.body.innerText"));
  };
  const click = async text => {
    const selector = `Array.from(document.querySelectorAll('button')).find(b=>b.textContent.trim()===${JSON.stringify(text)})`;
    await wait("!!" + selector); await evaluate(selector + ".click()");
  };
  const navigate = async route => {
    await send("Page.navigate", { url: base + "/#" + route });
    await wait("document.body.innerText.includes('Agent CF') && !document.body.innerText.includes('Đang tải…')");
  };
  const screenshot = async name => {
    const shot = await send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(dir + "/" + name + ".png", Buffer.from(shot.data, "base64"));
  };
  await send("Runtime.enable");
  await navigate("skills");
  await wait(`document.body.innerText.includes(${JSON.stringify(skills[0].name)})`);
  assert(!(await evaluate("document.body.innerText")).includes(skills[0].id));
  await evaluate(`Array.from(document.querySelectorAll('details')).find(d=>d.textContent.includes(${JSON.stringify(skills[0].id)})).querySelector('summary').click()`);
  assert((await evaluate("document.body.innerText")).includes(skills[0].id));
  await evaluate("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.__copied=text;}}})");
  await click("Sao chép ID");
  assert.equal(await evaluate("window.__copied"), skills[0].id);
  await screenshot("catalog-technical-open");
  await navigate("runs");
  await wait("!!document.querySelector('.runs-table tbody button')");
  assert(!(await evaluate("document.querySelector('.runs-table').innerText")).includes(history.items[0].id));
  await navigate("runs/" + history.items[0].id);
  await wait("document.body.innerText.includes('Thông tin chung')");
  await wait("!document.body.innerText.includes('Không tải được số phiên bản')");
  assert(!(await evaluate("document.body.innerText")).includes(history.items[0].id));
  assert(!(await evaluate("document.body.innerText")).includes(history.items[0].snapshot_sha256));
  await screenshot("run-default");
  await click("Tasks (" + history.items[0].task_runs.length + ")");
  for (const task of history.items[0].task_runs) assert(!(await evaluate("document.body.innerText")).includes(task.id));
  await navigate("projects/" + source.project.id);
  const row = `Array.from(document.querySelectorAll('tr')).find(r=>r.innerText.includes(${JSON.stringify(source.process.name)}))`;
  await wait("!!" + row);
  await evaluate(`Array.from((${row}).querySelectorAll('button')).find(b=>b.textContent.trim()==='Run').click()`);
  await wait("!!document.querySelector('#run-version')");
  assert.equal(await evaluate("document.querySelector('#run-version').value"), "Version " + source.version.version_number);
  assert(!(await evaluate("document.body.innerText")).includes(source.version.id));
  await send("Fetch.enable", { patterns: [{ urlPattern: "*://*/v1/runs", requestStage: "Request" }] });
  await evaluate("document.querySelector('dialog[open] form').requestSubmit()");
  await wait("document.body.innerText.includes('UI test: Run not created')");
  assert.equal(submitted.process_version_id, source.version.id);
  await send("Fetch.disable");
  await screenshot("run-form-version");
  await navigate("settings"); await click("Providers & Models API"); await click("Models API");
  await wait(`document.body.innerText.includes(${JSON.stringify(models[0].model_identifier)})`);
  assert(!(await evaluate("document.body.innerText")).includes(models[0].id));
  await navigate("pc");
  await wait("!!document.querySelector('[aria-label=\"Tìm PC\"]')");
  if (runners.length) {
    await click(runners[0].name);
    await wait("!!document.querySelector('dialog[open]')");
    assert(!(await evaluate("document.querySelector('dialog[open]').innerText")).includes(runners[0].id));
  }
  await navigate("agents");
  if (agents.length) {
    await wait(`document.body.innerText.includes(${JSON.stringify(agents[0].name)})`);
    assert(!(await evaluate("document.body.innerText")).includes(agents[0].id));
  }
  await navigate("overview");
  await wait("!document.body.innerText.includes('Đang tải tổng quan')");
  if (agents.length) await wait(`document.body.innerText.includes(${JSON.stringify(agents[0].name)})`);
  const overview = await evaluate("document.body.innerText");
  for (const row of [...roles, ...models]) assert(!overview.includes(row.id));
  await navigate("projects/" + source.project.id + "/processes/" + source.process.id);
  await wait(`document.body.innerText.includes(${JSON.stringify(source.process.name)})`);
  assert(!(await evaluate("document.body.innerText")).includes(source.version.id));
  await navigate("skills");
  await wait(`document.body.innerText.includes(${JSON.stringify(skills[0].name)})`);
  await evaluate(`Array.from(Array.from(document.querySelectorAll('tr')).find(row=>row.innerText.includes(${JSON.stringify(skills[0].name)})).querySelectorAll('button')).find(button=>button.textContent.trim()==='Versions').click()`);
  await wait("!!document.querySelector('.version-card')");
  const skillVersions = await get("/v1/skills/" + skills[0].id + "/versions");
  for (const version of skillVersions) assert(!(await evaluate("document.querySelector('dialog[open]').innerText")).includes(version.id));
  await navigate("robots");
  await wait("!!document.querySelector('table') || document.body.innerText.includes('Chưa có Robot')");
  assert.equal(errors.length, 0, JSON.stringify(errors));
  fs.writeFileSync(dir + "/result.json", JSON.stringify({ catalog_hidden:true, technical_copy_exact:true, run_ids_hidden:true,
    task_ids_hidden:true, run_form_number_visible:true, run_request_id_preserved:true, model_identifier_preserved:true, no_run_created:true, console_errors:errors }, null, 2));
  ws.close(); await fetch(cdp + "/json/close/" + target.id);
  console.log("Identifier UI regression passed; Run POST intercepted, no model call.");
})().catch(error => { console.error(error); process.exit(1); });
