// Read-only check: opens screens/Project menus without executing any action.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const base = process.env.BASE_URL || "http://127.0.0.1:5173";
const endpoint = process.env.CDP_URL || "http://127.0.0.1:9349";
const dir = process.env.ARTIFACT_DIR || "runtime/project-only-controls";
(async () => {
  fs.mkdirSync(dir, { recursive: true });
  const projects = await (await fetch(base + "/v1/projects")).json();
  assert(projects.length, "Needs an existing Project; no fixture is created.");
  const target = await (await fetch(endpoint + "/json/new?about:blank", { method: "PUT" })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  let id = 0; const pending = new Map(), errors = [], mutations = [];
  ws.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const p = pending.get(message.id); pending.delete(message.id);
      message.error ? p.reject(message.error) : p.resolve(message.result);
    }
    if (message.method === "Runtime.exceptionThrown") errors.push(message.params);
    if (message.method === "Network.requestWillBeSent" && !["GET", "HEAD", "OPTIONS"].includes(message.params.request.method)) mutations.push(message.params.request.url);
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const key = ++id; pending.set(key, { resolve, reject }); ws.send(JSON.stringify({ id: key, method, params }));
  });
  const evaluate = async expression => {
    const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    assert(!r.exceptionDetails, JSON.stringify(r.exceptionDetails)); return r.result.value;
  };
  const wait = async expression => {
    for (let n = 0; n < 150; n++) {
      if (await evaluate(expression)) return;
      await new Promise(resolve => setTimeout(resolve, 60));
    }
    throw Error("Timeout " + expression + "\n" + await evaluate("document.body.innerText"));
  };
  const click = async text => {
    const e = `Array.from(document.querySelectorAll('button')).find(b=>b.textContent.trim()===${JSON.stringify(text)})`;
    await wait("!!" + e); await evaluate(e + ".click()");
  };
  const check = async () => {
    const unwanted = await evaluate("Array.from(document.querySelectorAll('button,option')).map(e=>e.textContent.trim()).filter(t=>/^(Archive|Restore|Archived|Lưu trữ|Khôi phục|Đã lưu trữ)$/i.test(t))");
    assert.deepEqual(unwanted, []);
  };
  const navigate = async route => {
    await send("Page.navigate", { url: base + "/#" + route });
    await wait("!!document.querySelector('main') && !document.body.innerText.includes('Đang tải…')");
  };
  await send("Runtime.enable"); await send("Network.enable");
  for (const route of ["skills", "agents", "robots"]) {
    await navigate(route); await wait("document.body.innerText.includes('Thêm')"); await check();
    if (route === "skills") { await click("Tools"); await check(); }
  }
  await navigate("settings"); await click("Roles"); await check();
  await navigate("projects/" + projects[0].id);
  await wait(`document.body.innerText.includes(${JSON.stringify(projects[0].name)})`); await check();
  await navigate("projects");
  const project = projects[0];
  const trigger = `Array.from(document.querySelectorAll('[aria-haspopup=menu]')).find(e=>e.getAttribute('aria-label')===${JSON.stringify("Thao tác Project " + project.name)})`;
  await wait("!!" + trigger); await evaluate(trigger + ".click()");
  const label = project.status === "active" ? "Ngừng hoạt động" : "Kích hoạt lại";
  await wait(`Array.from(document.querySelectorAll('[role=menuitem]')).some(e=>e.textContent.trim()===${JSON.stringify(label)})`);
  assert(await evaluate("Array.from(document.querySelectorAll('option')).some(e=>e.textContent.trim()==='Không hoạt động')"));
  const shot = await send("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(dir + "/project-menu.png", Buffer.from(shot.data, "base64"));
  assert.deepEqual(errors, []); assert.deepEqual(mutations, []);
  fs.writeFileSync(dir + "/result.json", JSON.stringify({ no_archive_controls:true, project_toggle_preserved:true, project_status_filter_preserved:true, mutations, console_errors:errors }, null, 2));
  ws.close(); await fetch(endpoint + "/json/close/" + target.id);
  console.log("Project-only lifecycle controls: passed, no mutation requests.");
})().catch(error => { console.error(error); process.exit(1); });
