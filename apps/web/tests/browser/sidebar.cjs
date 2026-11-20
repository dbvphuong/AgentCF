// Navigation-only fixture: intercepts every API call; never changes the real DB.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.BASE_URL || 'http://127.0.0.1:5173';
const cdp = process.env.CDP_URL || 'http://127.0.0.1:9371';
const artifacts = process.env.ARTIFACT_DIR || 'runtime/sidebar-review';

(async () => {
  const target = await (await fetch(cdp + '/json/new?about:blank', { method: 'PUT' })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  let id = 0;
  const pending = new Map();
  const errors = [];
  ws.onmessage = ({ data }) => {
    const message = JSON.parse(data);
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails);
    if (!message.id) return;
    const promise = pending.get(message.id);
    pending.delete(message.id);
    message.error ? promise.reject(message.error) : promise.resolve(message.result);
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const key = ++id;
    pending.set(key, { resolve, reject });
    ws.send(JSON.stringify({ id: key, method, params }));
  });
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    assert(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const wait = async expression => {
    for (let i = 0; i < 100; i++) {
      if (await evaluate(expression)) return;
      await new Promise(resolve => setTimeout(resolve, 40));
    }
    throw Error('Timed out: ' + expression);
  };
  const settle = () => evaluate('new Promise(r => setTimeout(r, 200))');
  const screenshot = async (name, clip) => {
    const result = await send('Page.captureScreenshot', { format: 'png', ...(clip ? { clip } : {}) });
    fs.writeFileSync(`${artifacts}/${name}.png`, Buffer.from(result.data, 'base64'));
  };
  try {
    fs.mkdirSync(artifacts, { recursive: true });
    await send('Page.enable');
    await send('Runtime.enable');
    await send('Page.addScriptToEvaluateOnNewDocument', { source: `
      window.__mutations = [];
      const original = window.fetch;
      window.fetch = async (url, options = {}) => {
        const pathname = new URL(typeof url === 'string' ? url : url.url, location.href).pathname;
        if (pathname !== '/healthz' && !pathname.startsWith('/v1/')) return original(url, options);
        if (options.method && options.method !== 'GET') window.__mutations.push(pathname);
        let data = [];
        if (pathname === '/healthz') data = {status:'ok',database:{schema_version:23},temporal:{configured:false}};
        if (pathname === '/v1/overview/summary') data = {unresolved_errors:[],projects_progress:[],agents_token_usage:[],summary_stats:{unresolved_error_count:0,active_projects_count:0,active_agents_count:0}};
        if (pathname === '/v1/runs') data = {items:[],next_cursor:null,total:0,total_all:0};
        if (pathname === '/v1/settings/general') data = {default_task_timeout_seconds:300,default_logs_lines:100};
        return new Response(JSON.stringify(data), {headers:{'Content-Type':'application/json'}});
      };
    ` });
    await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 960, deviceScaleFactor: 1, mobile: false });
    await send('Page.navigate', { url: base + '/#skills' });
    await wait('document.querySelectorAll(".nav-item").length === 8 && document.querySelector(".brand-wordmark")?.naturalWidth > 0');
    const routes = ['overview', 'projects', 'runs', 'agents', 'skills', 'robots', 'pc', 'settings'];
    for (const route of routes) {
      await evaluate(`document.querySelector('.nav-item[href="#${route}"]').click()`);
      await wait(`document.querySelector('.nav-item[aria-current="page"]')?.getAttribute('href') === '#${route}'`);
      assert.equal(await evaluate('document.querySelectorAll(".nav-item[aria-current=page]").length'), 1);
    }
    // Parent menu stays selected for a nested route; unavailable fixture detail is harmless.
    await evaluate('location.hash="runs/new"');
    await wait('document.querySelector(".nav-item[aria-current=page]")?.hash === "#runs"');
    await evaluate('location.hash="skills"');
    await wait('document.querySelector(".nav-item.active")?.hash === "#skills"');
    await settle();
    await screenshot('desktop');
    await screenshot('sidebar', { x: 0, y: 0, width: 246, height: 740, scale: 2 });
    const box = await evaluate(`(() => { const r=document.querySelector('.nav-item[href="#projects"]').getBoundingClientRect(); return {x:r.x+60,y:r.y+r.height/2,width:r.width,height:r.height}; })()`);
    const style = () => evaluate(`(() => { const e=document.querySelector('.nav-item[href="#projects"]'); const s=getComputedStyle(e); const r=e.getBoundingClientRect(); return {background:s.backgroundColor,x:r.x,y:r.y,width:r.width,height:r.height,transform:s.transform}; })()`);
    const idle = await style();
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y });
    await settle();
    const hover = await style();
    assert.notEqual(hover.background, idle.background);
    assert.equal(hover.transform, 'none');
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: box.x, y: box.y, button: 'left', clickCount: 1 });
    await settle();
    const pressed = await style();
    assert.notEqual(pressed.background, hover.background);
    assert.equal(pressed.width, idle.width);
    assert.equal(pressed.y, idle.y);
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: box.x, y: box.y, button: 'left', clickCount: 1 });
    await wait('document.querySelector(".nav-item.active")?.hash === "#projects"');
    // Real Tab and Enter input, rather than programmatic focus/click.
    await evaluate('document.activeElement.blur(); document.querySelector(".brand").focus()');
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
    assert.equal(await evaluate('document.activeElement.hash'), '#overview');
    assert(await evaluate('document.activeElement.matches(":focus-visible")'));
    assert.equal(await evaluate('getComputedStyle(document.activeElement).outlineWidth'), '2px');
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
    await wait('document.querySelector(".nav-item.active")?.hash === "#overview"');
    // Command palette still uses the same navigation catalog.
    await evaluate('document.querySelector(".quick-search").click()');
    await wait('document.querySelectorAll(".command-option").length === 8');
    await evaluate('Array.from(document.querySelectorAll(".command-option")).find(e=>e.textContent.trim()==="Skills").click()');
    await wait('!document.querySelector("dialog[open]") && document.querySelector(".nav-item.active")?.hash === "#skills"');
    await send('Emulation.setDeviceMetricsOverride', { width: 800, height: 800, deviceScaleFactor: 1, mobile: false });
    assert(await evaluate('document.querySelector(".brand-wordmark").getBoundingClientRect().right < document.querySelector(".sidebar").getBoundingClientRect().right'));
    await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    await evaluate('document.querySelector(".mobile-menu").click()');
    await wait('document.querySelector(".sidebar.open") !== null');
    await settle();
    await screenshot('mobile');
    await evaluate(`document.querySelector('.nav-item[href="#projects"]').click()`);
    await wait('!document.querySelector(".sidebar.open") && document.querySelector(".nav-item.active")?.hash === "#projects"');
    await evaluate('document.querySelector(".mobile-menu").click()');
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
    await wait('!document.querySelector(".sidebar.open")');
    await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
    assert(await evaluate('Array.from(document.querySelectorAll(".sidebar, .brand, .nav-item, .nav-icon")).every(e=>getComputedStyle(e).transitionDuration === "0s")'));
    assert.deepEqual(await evaluate('window.__mutations'), []);
    assert.deepEqual(errors, []);
    const report = { passed: true, routes: 8, nestedRoute: true, hover: true, press: true, noLayoutShift: true, keyboard: true, commandPalette: true, tablet: true, mobile: true, reducedMotion: true, apiMutations: 0, javascriptErrors: 0 };
    fs.writeFileSync(`${artifacts}/browser.json`, JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally {
    await send('Page.close');
    ws.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
