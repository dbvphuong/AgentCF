// Deletion display fixture: all API requests intercepted; no real data is deleted.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.BASE_URL || 'http://127.0.0.1:5173';
const cdp = process.env.CDP_URL || 'http://127.0.0.1:9371';
const artifacts = process.env.ARTIFACT_DIR || 'runtime/deletion-feedback';

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
  const clickText = async (text, selector = 'button') => {
    const expression = 'Array.from(document.querySelectorAll(' + JSON.stringify(selector) + ')).find(e=>e.textContent.trim()===' + JSON.stringify(text) + ')';
    await wait('!!' + expression);
    await evaluate(expression + '.click()');
  };
  try {
    fs.mkdirSync(artifacts, { recursive: true });
    await send('Page.enable');
    await send('Runtime.enable');
    await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 960, deviceScaleFactor: 1, mobile: false });
    await send('Page.addScriptToEvaluateOnNewDocument', { source: `
      window.__deleted = new Set();
      window.__allowDelete = false;
      const nativeFetch = window.fetch;
      const rows = {
        '/v1/settings/providers': [{id:'provider-opaque',name:'Provider thử',api_format:'custom',base_url:'http://localhost',status:'active'}],
        '/v1/settings/models': [{id:'model-opaque',name:'Model viết bài',provider_id:'provider-opaque',model_identifier:'exact',status:'active'}],
        '/v1/settings/roles': [{id:'role-opaque',name:'Biên tập'}],
        '/v1/skills': [{id:'skill-opaque',name:'Skill nội dung',is_global:true,status:'active'}],
        '/v1/skills/tools': [{id:'tool-opaque',name:'Tool tìm kiếm',tool_type:'internal',status:'active'}],
        '/v1/agents': [{id:'agent-opaque',name:'Agent biên tập',status:'active'}],
        '/v1/robots': [{id:'robot-opaque',name:'Robot tài liệu',status:'active'}],
        '/v1/runners': [{id:'pc-opaque',name:'PC biên tập',status:'online',display_status:'online'}],
        '/v1/projects': [{id:'project-opaque',name:'Project video',pm_name:'Agent biên tập',status:'active'}],
      };
      window.fetch = async (url, options={}) => {
        const path = new URL(typeof url==='string'?url:url.url,location.href).pathname;
        const json=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
        if (path !== '/healthz' && !path.startsWith('/v1/')) return nativeFetch(url,options);
        if (options.method === 'DELETE') {
          if (!window.__allowDelete) return json({detail:window.__error}, path.startsWith('/v1/projects')||path.startsWith('/v1/processes')?422:409);
          window.__deleted.add(path.split('/').pop());
          return path.startsWith('/v1/projects')||path.startsWith('/v1/processes')?json({deleted:true}):new Response(null,{status:204});
        }
        if (path === '/healthz') return json({status:'ok',database:{schema_version:23},temporal:{configured:false}});
        if (rows[path]) return json(rows[path].filter(r=>!window.__deleted.has(r.id)));
        if (path === '/v1/projects/project-opaque') return json({...rows['/v1/projects'][0],workspace_id:'workspace',team:[],targets:[],processes:[{id:'process-opaque',name:'Process xuất bản',status:'active'}]});
        if (path === '/v1/overview/summary') return json({agents_token_usage:[],projects_progress:[],unresolved_errors:[],summary_stats:{}});
        if (path.endsWith('/statistics')) return json({overall:{success_rate:null}});
        return json([]);
      };
    ` });
    const cases = [
      {route:'settings',name:'Provider thử',error:'Không thể xóa Provider “Provider thử” vì còn Model API liên kết: “Model viết bài”. Vào Models API để xóa model này trước.'},
      {route:'settings',tab:'Models API',name:'Model viết bài',error:'Không thể xóa Model API “Model viết bài” vì Agent “Agent biên tập” đang sử dụng. Đổi model trong Agent điều phối trước.'},
      {route:'settings',tab:'Roles',name:'Biên tập',error:'Không thể xóa Role “Biên tập” vì Agent “Agent biên tập” đang sử dụng. Đổi Role trước khi xóa.'},
      {route:'skills',name:'Skill nội dung',error:'Skill “Skill nội dung” đang được sử dụng trong Process “Process xuất bản”, Project “Project video”, bước “Viết bài”. Gỡ tham chiếu trước khi xóa.'},
      {route:'skills',tab:'Tools',name:'Tool tìm kiếm',error:'Không thể xóa Tool “Tool tìm kiếm” vì Skill “Skill nội dung” v1 và Agent “Agent biên tập” còn liên kết. Gỡ Tool trước khi xóa.'},
      {route:'agents',name:'Agent biên tập',error:'Agent “Agent biên tập” đang được dùng tại bước “Viết bài”, Process “Process xuất bản”, Project “Project video”. Gỡ tham chiếu trước khi xóa.'},
      {route:'robots',name:'Robot tài liệu',error:'Không thể xóa Robot “Robot tài liệu” vì đã có phiên bản v1 được phát hành. Phiên bản đã phát hành được giữ bất biến.'},
      {route:'pc',name:'PC biên tập',error:'Không thể xóa PC “PC biên tập” vì Process “Process xuất bản”, Project “Project video”, Run tạo lúc 20/11/2026 08:02:03 đang chạy. Vào Runs để dừng.'},
      {route:'projects',name:'Project video',menu:true,error:'Không thể xóa Project “Project video” vì Process “Process xuất bản” còn Run chưa kết thúc. Vào Runs để dừng và chờ kết thúc.'},
      {route:'projects/project-opaque',name:'Process xuất bản',error:'Không thể xóa Process “Process xuất bản” trong Project “Project video” vì PC “PC biên tập” chưa xác nhận dừng. Kiểm tra Client và chờ xác nhận.'},
    ];
    for (const item of cases) {
      await send('Page.navigate', { url: base + '/#' + item.route });
      await wait('!!document.querySelector("main")');
      if (item.tab) await clickText(item.tab);
      await evaluate('window.__allowDelete=false; window.__error=' + JSON.stringify(item.error));
      if (item.menu) {
        await wait('!!document.querySelector(".project-actions-trigger")');
        await evaluate('document.querySelector(".project-actions-trigger").click()');
        await clickText('Xóa');
      } else {
        const row = 'Array.from(document.querySelectorAll("tbody tr")).find(e=>e.textContent.includes(' + JSON.stringify(item.name) + '))';
        await wait('!!' + row);
        await evaluate('Array.from((' + row + ').querySelectorAll("button")).find(e=>e.textContent.trim()==="Xóa").click()');
      }
      await wait('!!document.querySelector("dialog[open]")');
      await evaluate('document.querySelector("dialog[open] .form-actions button:last-child").click()');
      await wait('document.querySelector("dialog[open] [role=alert]")?.textContent === ' + JSON.stringify(item.error));
      assert.equal(await evaluate('document.querySelector("dialog[open] [role=alert]").textContent'), item.error);
      assert(!(await evaluate('document.querySelector("dialog[open]").textContent.includes("-opaque")')));
      if (item.route==='settings' && !item.tab) await screenshot('provider-error');
      if (item.route==='robots') {
        assert.equal(await evaluate('location.hash'), '#robots', 'Delete must not trigger row navigation');
        await screenshot('robot-error');
        await evaluate('window.__allowDelete=true');
        await clickText('Xác nhận', 'dialog[open] button');
        await wait('!document.querySelector("dialog[open]") && !document.querySelector("tbody")?.textContent.includes("Robot tài liệu")');
      }
      console.log('passed: ' + item.route + ' ' + (item.tab || item.name));
    }
    assert.deepEqual(errors, []);
    const report={passed:true,deletionScreens:cases.length,robotRetry:true,javascriptErrors:0,realApiRequests:0};
    fs.writeFileSync(artifacts+'/browser.json',JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));
  } finally {
    await send('Page.close');
    ws.close();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
