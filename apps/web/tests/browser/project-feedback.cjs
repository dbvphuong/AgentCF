// UI regression with intercepted Project responses; never mutates the real Server.
// Requires Web at BASE_URL and a dedicated browser at CDP_URL.
const assert = require("node:assert/strict");
const base = process.env.BASE_URL || "http://127.0.0.1:5173";
const cdp = process.env.CDP_URL || "http://127.0.0.1:9367";

(async () => {
  const tab = await (await fetch(cdp + "/json/new?about:blank", { method: "PUT" })).json();
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  let sequence = 0;
  const pending = new Map();
  ws.onmessage = ({ data }) => {
    const message = JSON.parse(data);
    if (!message.id) return;
    const p = pending.get(message.id);
    pending.delete(message.id);
    message.error ? p.reject(message.error) : p.resolve(message.result);
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async (expression) => {
    const result = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    assert(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const wait = async (condition) => {
    for (let i = 0; i < 100; i++) {
      if (await evaluate(condition)) return;
      await new Promise(resolve => setTimeout(resolve, 80));
    }
    throw Error("Timed out: " + condition);
  };
  const click = async (selector) => {
    await wait(`!!document.querySelector(${JSON.stringify(selector)})`);
    await evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
  };
  try {
    await send("Page.enable");
    await send("Page.addScriptToEvaluateOnNewDocument", { source: `
      window.__deleteMode = "error";
      window.__projects = [{id:"feedback-fixture", name:"Project kiểm tra", status:"active", description:"Test UI", pm_name:"PM"}];
      const nativeFetch = window.fetch;
      window.fetch = async (url, options = {}) => {
        const path = new URL(typeof url === "string" ? url : url.url, location.href).pathname;
        const json = (value, status = 200) => Promise.resolve(new Response(JSON.stringify(value), {status, headers:{"Content-Type":"application/json"}}));
        if (path === "/v1/projects/feedback-fixture" && options.method === "DELETE") {
          if (window.__deleteMode === "error") return json({detail:"Còn Run chưa kết thúc; không thể xóa"}, 422);
          window.__projects=[]; return json({deleted:true});
        }
        if (path === "/v1/projects/feedback-fixture") return json({...window.__projects[0],workspace_id:"ws",pm_agent_id:"pm",team:[{id:"pm",name:"PM",status:"active"}],targets:[],processes:[{id:"process-fixture",name:"Process test",status:"active"}]});
        if (path === "/v1/agents") return json([{id:"pm",name:"PM",status:"active"},{id:"employee",name:"New employee",status:"active"}]);
        if (path === "/v1/processes/process-fixture") return json({id:"process-fixture",name:"Process test",versions:[{id:"version-fixture",version_number:1,revision:1,status:"draft",definition:{definition_format_version:"1",interpreter_version:"dag-v1",tasks:[],dependencies:[]}}]});
        if (path === "/v1/projects") return json(window.__projects);
        if (path.startsWith("/v1/")) return json([]);
        return nativeFetch(url, options);
      };
    ` });
    await send("Page.navigate", { url: base + "/#projects" });
    await wait('!!document.querySelector(".project-actions-trigger")');
    await click('a[href="#projects/feedback-fixture"]');
    await wait('!!document.querySelector(".project-context .project-back-link")');
    assert(await evaluate('document.querySelector(".project-context").textContent.includes("PM:")'));
    assert(!(await evaluate('document.querySelector(".page-heading").textContent.includes("← Projects")')));
    assert(await evaluate('(()=>{const p=document.querySelector(".project-context");const a=p.querySelector("a").getBoundingClientRect();const last=p.lastElementChild.getBoundingClientRect();return Math.abs(a.top-last.top)<5;})()'), "Back link shares the existing description/PM row");
    await evaluate(`Array.from(document.querySelectorAll('button')).find(e=>e.textContent.trim()==='Team').click()`);
    await wait('document.body.textContent.includes("Tự tổng hợp")');
    assert(!(await evaluate(`Array.from(document.querySelectorAll('button')).some(e=>/Manage team|Quản lý Team/.test(e.textContent))`)));
    await evaluate(`Array.from(document.querySelectorAll('button')).find(e=>e.textContent.trim()==='Processes').click()`);
    await click('a[href*="process-fixture"]');
    await wait(`Array.from(document.querySelectorAll('button')).some(e=>e.textContent.trim()==='+ Bước AI / Skill')`);
    await evaluate(`Array.from(document.querySelectorAll('button')).find(e=>e.textContent.trim()==='+ Bước AI / Skill').click()`);
    await wait('!!document.querySelector("dialog[open] form")');
    assert(!(await evaluate('document.querySelector("dialog[open]").textContent.includes("Quản lý Team")')));
    assert(await evaluate(`(()=>{const l=Array.from(document.querySelectorAll('dialog[open] label')).find(l=>l.textContent.includes('Agent điều phối'));return Array.from(document.getElementById(l.htmlFor).options).some(o=>o.value==='employee');})()`), "Agent outside the displayed Team is selectable directly");
    await click('dialog[open] [aria-label="Đóng"]');
    await evaluate('location.hash="projects/feedback-fixture/team"');
    await wait('!!document.querySelector(".project-context .project-back-link")');
    await click('.project-context .project-back-link');
    await wait('!!document.querySelector(".projects-list")');
    // Exercise the All filter without mutating any real Project.
    await evaluate(`(() => {const e=document.querySelector('[aria-label="Trạng thái Project"]'); Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(e,'all');e.dispatchEvent(new Event('change',{bubbles:true}));})()`);
    const remove = async () => {
      await click(".project-actions-trigger");
      await wait(`Array.from(document.querySelectorAll('[role="menuitem"]')).some(e=>e.textContent.trim()==='Xóa')`);
      await evaluate(`Array.from(document.querySelectorAll('[role="menuitem"]')).find(e=>e.textContent.trim()==='Xóa').click()`);
      await click("dialog[open] .btn-danger");
    };
    await remove();
    await wait('!!document.querySelector(".toast-error")');
    assert.equal(await evaluate('document.querySelector(".toast").getAttribute("role")'), "alert");
    assert.match(await evaluate('document.querySelector(".toast").textContent'), /Còn Run chưa kết thúc/);
    assert(await evaluate('!!document.querySelector("dialog[open]")'));
    assert(await evaluate('(()=>{const e=document.querySelector(\'.toast [aria-label="Đóng thông báo"]\');const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));})()'), "Error toast close button must be above the native dialog backdrop");
    await click('.toast [aria-label="Đóng thông báo"]');
    await wait('!document.querySelector(".toast")');
    await evaluate('window.__deleteMode="deleted"');
    await click("dialog[open] .btn-danger");
    await wait('!!document.querySelector(".toast-success") && !document.querySelector("dialog[open]")');
    assert.match(await evaluate('document.querySelector(".toast").textContent'), /Đã xóa/);
    assert(await evaluate('(()=>{const r=document.querySelector(".toast").getBoundingClientRect();return r.top<30 && innerWidth-r.right<30;})()'));
    await wait('!document.querySelector(".project-actions-trigger")');
    await send("Emulation.setDeviceMetricsOverride", { width:390, height:844, deviceScaleFactor:1, mobile:true });
    assert(await evaluate('(()=>{const r=document.querySelector(".toast").getBoundingClientRect();return r.left>=0 && r.right<=innerWidth;})()'));
    await wait('!document.querySelector(".toast")');
    console.log("PASS: Project deletion error/success, retry, auto-dismiss, manual close, desktop/mobile placement; mocked mutations only.");
  } finally {
    await send("Page.close");
    ws.close();
  }
})().catch(error => { console.error(error); process.exitCode=1; });
