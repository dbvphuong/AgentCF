// Run against an isolated Server DB: BASE_URL=http://127.0.0.1:5178 CDP_URL=http://127.0.0.1:9338.
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
    await send("Runtime.enable");
    await send("Page.enable");
    await send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 1000,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await send("Page.navigate", { url: base });
    await wait('document.querySelectorAll(".nav-item").length === 8');
    const suffix = Date.now().toString(36);
    const provider = {
      id: "provider-" + suffix,
      name: "Local " + suffix,
      api_format: "custom",
      base_url: "http://127.0.0.1:18080/healthz",
    };
    await api("/v1/settings/providers", provider);
    await api("/v1/settings/models", {
      id: "model-" + suffix,
      provider_id: provider.id,
      name: "Exact runtime model " + suffix,
      model_identifier: "runtime-model-id",
    });
    await api("/v1/settings/roles", {
      id: "role-" + suffix,
      name: "Reviewer " + suffix,
    });
    const workspace = await api("/v1/workspaces", {
      name: "Browser workspace " + suffix,
    });
    // Create a new Skill and immutable version entirely through the Web.
    await navigate("skills");
    await clickText("+ Thêm mới");
    await fill("Tên", "Browser skill " + suffix);
    await fill("Mô tả", "Configured through UI, no fixture edits");
    await evaluate("Array.from(document.querySelectorAll('dialog[open] label')).find(l=>l.textContent.includes('Global (tất cả Project)')).querySelector('input').click()");
    await submit();
    await wait('document.querySelectorAll("dialog[open]").length === 0');
    const skill = (await api("/v1/skills", undefined, "GET")).find(
      (s) => s.name === "Browser skill " + suffix,
    );
    assert(skill);
    await wait(
      `Array.from(document.querySelectorAll('tr')).some(row=>row.textContent.includes(${JSON.stringify("Browser skill ")}+${JSON.stringify(suffix)}))`,
    );
    await evaluate(
      `Array.from(document.querySelectorAll('tr')).find(row=>row.textContent.includes(${JSON.stringify("Browser skill ")}+${JSON.stringify(suffix)})).querySelectorAll('button')[1].click()`,
    );
    await clickText("+ Draft version");
    await fill("Hướng dẫn", "Analyze any supplied input.");
    await fill("Expected output", "A structured report.");
    await evaluate(
      `Array.from(document.querySelectorAll('dialog[open]')).at(-1).querySelector('form').requestSubmit()`,
    );
    await wait(
      'document.querySelector(".version-card")?.textContent.includes("draft")',
    );
    await clickText("Version 1");
    await clickText("Sửa draft");
    await fill(
      "Hướng dẫn",
      "Analyze any supplied input after editing the draft.",
    );
    await submit();
    await wait('!document.querySelector("dialog[open] form")');
    await clickText("Publish");
    await clickText("Xác nhận");
    await wait(
      'document.querySelector(".version-card")?.textContent.includes("published")',
    );
    await close();
    await navigate("agents");
    await clickText("+ Thêm mới");
    await fill("Tên", "Browser agent " + suffix);
    await fill("Role", "role-" + suffix);
    await fill("Model", "model-" + suffix);
    await fill("Hướng dẫn cơ sở", "Review deliverables.");
    await submit();
    await wait('document.querySelectorAll("dialog[open]").length === 0');
    const agent = (await api("/v1/agents", undefined, "GET")).find(
      (a) => a.name === "Browser agent " + suffix,
    );
    assert(agent);
    // Project, target, process, graph and publishing from the same UI.
    await navigate("projects");
    const createProjectSelector = JSON.stringify('[aria-label="Tạo Project"]');
    await wait(`!!document.querySelector(${createProjectSelector})`);
    await evaluate(`document.querySelector(${createProjectSelector}).click()`);
    await fill("Tên", "Browser project " + suffix);
    await fill("Mô tả", "Sản xuất và duyệt nội dung video cho kênh YouTube.");
    await fill("Workspace", workspace.id);
    await fill("PM", agent.id);
    await submit();
    await wait('document.querySelectorAll("dialog[open]").length === 0');
    await wait('!!document.querySelector(".projects-table th")');
    assert.deepEqual(
      await evaluate(
        'Array.from(document.querySelectorAll(".projects-table th")).map(e=>e.textContent.trim())',
      ),
      ["Project", "Mô tả", "PM", "Trạng thái", "Thao tác"],
    );
    await clickText("Browser project " + suffix, "a");
    await clickText("Targets");
    await clickText("+ Target");
    await fill("Tên mục tiêu", "Approved reports");
    await fill("Bắt đầu", "2026-11-01");
    await fill("Kết thúc", "2026-11-30");
    await fill("Số lượng mục tiêu", "10");
    await fill("Kết quả được duyệt", "2");
    await fill("Tiêu chí nghiệm thu", "Reviewed and approved");
    await submit();
    await wait('document.querySelectorAll("dialog[open]").length === 0');
    await clickText("Processes");
    await clickText("+ Process");
    await fill("Tên", "Browser process " + suffix);
    await submit();
    await wait('document.querySelectorAll("dialog[open]").length === 0');
    await clickText("Browser process " + suffix, "a");
    await clickText("+ Bước AI / Skill");
    await fill("Tên bước", "Analyze");
    await fill("Agent điều phối", agent.id);
    await fill("Skill", skill.id);
    await fill("Model thực thi", "cli-codex-sol");
    await submit();
    await wait(
      'document.querySelectorAll(".graph-node:not(.start-node)").length === 1',
    );
    await clickText("Lưu draft");
    await wait('document.body.innerText.includes("Đã lưu draft.")');
    await clickText("Validate");
    await wait('document.body.innerText.includes("Cấu hình hợp lệ")');
    await clickText("Publish");
    await clickText("Xác nhận");
    await wait('document.body.innerText.includes("Tạo / mở draft")');
    const editorHash = await evaluate("location.hash");
    await send("Page.reload");
    await wait('document.body.innerText.includes("Tạo / mở draft")');
    assert.equal(
      await evaluate(
        'document.querySelectorAll(".graph-node:not(.start-node)").length',
      ),
      1,
    );
    // Persisted node positions can be dragged without changing a published graph.
    await clickText("Tạo / mở draft");
    await wait('document.body.innerText.includes("Lưu draft")');
    const rect = await evaluate(
      '(() => { const r = document.querySelector(".graph-node:not(.start-node)").getBoundingClientRect(); return {x:r.x+80,y:r.y+30}; })()',
    );
    await send("Input.dispatchMouseEvent", {
      type: "mousePressed",
      x: rect.x,
      y: rect.y,
      button: "left",
      clickCount: 1,
    });
    await send("Input.dispatchMouseEvent", {
      type: "mouseMoved",
      x: rect.x + 95,
      y: rect.y + 70,
      button: "left",
      buttons: 1,
    });
    await send("Input.dispatchMouseEvent", {
      type: "mouseReleased",
      x: rect.x + 95,
      y: rect.y + 70,
      button: "left",
      clickCount: 1,
    });
    await wait('document.body.innerText.includes("Chưa lưu")');
    await clickText("Lưu draft");
    await wait('document.body.innerText.includes("Đã lưu draft.")');
    const graphShot = await send("Page.captureScreenshot", { format: "png" });
    fs.mkdirSync(artifacts, { recursive: true });
    fs.writeFileSync(
      path.join(artifacts, "process-editor-1440.png"),
      Buffer.from(graphShot.data, "base64"),
    );
    await clickText("← Project");
    await clickText("Schedule");
    await clickText("+ Schedule");
    await fill("Tên lịch", "Daily browser check");
    const processId = decodeURIComponent(editorHash.split("/").at(-1));
    const published = (
      await api("/v1/processes/" + processId, undefined, "GET")
    ).versions.find((v) => v.status === "published");
    await fill("Version", published.id);
    assert(
      await evaluate(
        'Array.from(document.querySelectorAll("dialog[open]")).at(-1).querySelector("form").checkValidity()',
      ),
      JSON.stringify(
        await evaluate(
          'Array.from(document.querySelectorAll("dialog[open] input,dialog[open] select,dialog[open] textarea")).filter(e=>!e.checkValidity()).map(e=>({id:e.id,value:e.value,message:e.validationMessage}))',
        ),
      ),
    );
    await submit();
    await wait('!!document.querySelector(".version-card")');
    await clickText("Start");
    await clickText("Xác nhận");
    await wait(
      'document.querySelector(".version-card")?.textContent.includes("Started")',
    );
    await clickText("Stop");
    await clickText("Xác nhận");
    await wait(
      'document.querySelector(".version-card")?.textContent.includes("Stopped")',
    );
    await close();
    await clickText("Run");
    await fill("Input JSON", '{"arbitrary":"browser input"}');
    await submit();
    await wait(
      'location.hash.startsWith("#runs/") && !location.hash.endsWith("new")',
    );
    await wait('document.body.innerText.includes("Hủy lượt chạy")');
    // Native confirmation must be handled through CDP, preserving real click behavior.
    const autoConfirm = async (event) => {
      const m = JSON.parse(event.data);
      if (m.method === "Page.javascriptDialogOpening")
        await send("Page.handleJavaScriptDialog", { accept: true });
    };
    ws.addEventListener("message", autoConfirm);
    await clickText("Hủy lượt chạy");
    await wait('document.body.innerText.includes("CANCELLED")');
    ws.removeEventListener("message", autoConfirm);

    // Project menu: keyboard/outside dismissal, clone, and confirmation before mutations.
    const projectMenu = async (name) => {
      await wait(
        `!!Array.from(document.querySelectorAll('.projects-table tbody tr')).find(r=>r.textContent.includes(${JSON.stringify(name)}))`,
      );
      await evaluate(
        `Array.from(document.querySelectorAll('.projects-table tbody tr')).find(r=>r.textContent.includes(${JSON.stringify(name)})).querySelector('[aria-haspopup="menu"]').click()`,
      );
      await wait('!!document.querySelector(".project-action-menu")');
    };
    const projectFilter = async (value) => {
      await evaluate(
        `(() => { const e=document.querySelector('[aria-label="Trạng thái Project"]'); Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(e,${JSON.stringify(value)}); e.dispatchEvent(new Event('change',{bubbles:true})); })()`,
      );
      await evaluate(
        "new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))",
      );
    };
    await navigate("projects");
    await projectMenu("Browser project " + suffix);
    assert.deepEqual(
      await evaluate(
        'Array.from(document.querySelectorAll(".project-action-menu [role=menuitem]")).map(e=>e.textContent.trim())',
      ),
      ["Sửa", "Nhân bản", "Ngừng hoạt động", "Xóa"],
    );
    await send("Input.dispatchKeyEvent", {
      type: "keyDown",
      key: "ArrowDown",
      code: "ArrowDown",
      windowsVirtualKeyCode: 40,
    });
    assert.equal(
      await evaluate("document.activeElement.textContent.trim()"),
      "Nhân bản",
    );
    await send("Input.dispatchKeyEvent", {
      type: "keyDown",
      key: "Escape",
      code: "Escape",
      windowsVirtualKeyCode: 27,
    });
    await wait('!document.querySelector(".project-action-menu")');
    assert(
      await evaluate(
        'document.activeElement.getAttribute("aria-haspopup")==="menu"',
      ),
    );
    await projectMenu("Browser project " + suffix);
    await evaluate(
      'document.querySelector(".page-heading h1").dispatchEvent(new PointerEvent("pointerdown",{bubbles:true}))',
    );
    await wait('!document.querySelector(".project-action-menu")');
    await projectMenu("Browser project " + suffix);
    await clickText("Nhân bản", '[role="menuitem"]');
    const cloneName = "Browser project copy " + suffix;
    await fill("Tên Project mới", cloneName);
    await submit();
    await wait('document.querySelectorAll("dialog[open]").length === 0');
    const copiedProject = (await api("/v1/projects", undefined, "GET")).find(
      (p) => p.name === cloneName,
    );
    assert(copiedProject);
    const copiedDetails = await api(
      "/v1/projects/" + copiedProject.id,
      undefined,
      "GET",
    );
    assert.equal(copiedDetails.targets[0].completed_count, 2);
    assert.equal(
      (await api("/v1/runs?project_id=" + copiedProject.id, undefined, "GET"))
        .total,
      0,
    );
    assert.equal(
      (
        await api(
          "/v1/processes/" + copiedDetails.processes[0].id + "/schedules",
          undefined,
          "GET",
        )
      ).items[0].is_active,
      false,
    );
    await projectMenu(cloneName);
    await clickText("Ngừng hoạt động", '[role="menuitem"]');
    await clickText("Quay lại", "dialog[open] button");
    assert.equal(
      (await api("/v1/projects/" + copiedProject.id, undefined, "GET")).status,
      "active",
    );
    await projectMenu(cloneName);
    await clickText("Ngừng hoạt động", '[role="menuitem"]');
    await clickText("Ngừng hoạt động", "dialog[open] button");
    await wait('document.querySelectorAll("dialog[open]").length === 0');
    await projectFilter("archived");
    await wait('!!document.querySelector(".project-status.is-inactive")');
    assert.equal(
      await evaluate(
        'document.querySelector(".project-status.is-inactive").textContent.trim()',
      ),
      "Không hoạt động",
    );
    await projectMenu(cloneName);
    await clickText("Kích hoạt lại", '[role="menuitem"]');
    await clickText("Kích hoạt lại", "dialog[open] button");
    await wait('document.querySelectorAll("dialog[open]").length === 0');
    await projectFilter("active");
    await projectMenu(cloneName);
    await clickText("Xóa", '[role="menuitem"]');
    await clickText("Quay lại", "dialog[open] button");
    assert.equal(
      (await api("/v1/projects/" + copiedProject.id, undefined, "GET")).status,
      "active",
    );
    await projectMenu(cloneName);
    await clickText("Xóa", '[role="menuitem"]');
    await clickText("Xóa Project", "dialog[open] button");
    await wait('document.querySelectorAll("dialog[open]").length === 0');
    assert.equal(
      (await api("/v1/projects/" + copiedProject.id, undefined, "GET")).status,
      "archived",
    );

    await navigate("pc");
    await clickText("+ Connect PC");
    await fill("Workspace", workspace.id);
    await fill("Tên PC", "Browser PC");
    await submit();
    await wait(
      'document.querySelector(".pairing-code")?.textContent.length > 4',
    );
    const pairingCode = await evaluate(
      'document.querySelector(".pairing-code").textContent',
    );
    assert(pairingCode);
    await close();
    // Pair with API as a Client would, then validate PC controls in the UI.
    await api("/v1/runners/pair", {
      pairing_code: pairingCode,
      client_version: "browser-test",
    });
    await clickText("Làm mới");
    await wait('document.body.innerText.includes("Browser PC")');
    await clickText("Sửa");
    await fill("Tên PC", "Browser PC renamed");
    await submit();
    await wait('document.body.innerText.includes("Browser PC renamed")');
    await clickText("Xóa", "tbody button");
    await clickText("Xóa PC", "dialog[open] button");
    await wait('!document.body.innerText.includes("Browser PC renamed")');
    // Verify that all menus render at desktop and mobile sizes, without horizontal page overflow.
    fs.mkdirSync(artifacts, { recursive: true });
    for (const width of [1440, 390]) {
      await send("Emulation.setDeviceMetricsOverride", {
        width,
        height: width === 390 ? 844 : 1000,
        deviceScaleFactor: 1,
        mobile: width === 390,
      });
      for (const route of [
        "overview",
        "projects",
        "runs",
        "agents",
        "skills",
        "robots",
        "pc",
        "settings",
      ]) {
        await navigate(route);
        await new Promise((r) => setTimeout(r, 180));
        assert(
          await evaluate(
            "document.documentElement.scrollWidth <= innerWidth + 1",
          ),
          `Page overflow: ${route}, ${width}`,
        );
        const shot = await send("Page.captureScreenshot", {
          format: "png",
          captureBeyondViewport: false,
        });
        fs.writeFileSync(
          path.join(artifacts, `${route}-${width}.png`),
          Buffer.from(shot.data, "base64"),
        );
        if (route === "projects") {
          const scroll =
            'document.querySelector(".projects-list .table-scroll")';
          await evaluate(`${scroll}.scrollLeft=${scroll}.scrollWidth`);
          await projectMenu("Browser project " + suffix);
          await evaluate(
            "new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))",
          );
          assert(
            await evaluate('!!document.querySelector(".project-action-menu")'),
            `Project menu closed immediately at ${width}`,
          );
          assert(
            await evaluate(
              '(() => {const r=document.querySelector(".project-action-menu").getBoundingClientRect();const v=visualViewport;const x=v?.offsetLeft??0,y=v?.offsetTop??0;return r.left>=x&&r.right<=x+(v?.width??innerWidth)&&r.top>=y&&r.bottom<=y+(v?.height??innerHeight);})()',
            ),
            `Project menu outside viewport ${width}`,
          );
          const menuShot = await send("Page.captureScreenshot", {
            format: "png",
            captureBeyondViewport: false,
          });
          fs.writeFileSync(
            path.join(artifacts, `project-menu-${width}.png`),
            Buffer.from(menuShot.data, "base64"),
          );
          await send("Input.dispatchKeyEvent", {
            type: "keyDown",
            key: "Escape",
            code: "Escape",
            windowsVirtualKeyCode: 27,
          });
        }
      }
    }
    await navigate(editorHash);
    await wait('!!document.querySelector(".process-builder")');
    assert(
      await evaluate("document.documentElement.scrollWidth <= innerWidth + 1"),
      "Mobile editor overflow",
    );
    assert.equal(errors.length, 0, JSON.stringify(errors));
    console.log(
      JSON.stringify({
        passed: true,
        menus: 8,
        viewportChecks: 17,
        uiFlows: [
          "skill/version/publish",
          "agent",
          "project",
          "project/menu/keyboard/clone/deactivate/activate/delete-confirmations",
          "target",
          "process/editor/drag/publish/reload",
          "schedule/save/start/stop",
          "run/create/cancel",
          "PC pairing/disable",
        ],
        runtimeExecution: false,
      }),
    );
  } finally {
    ws.close();
    await fetch(endpoint + "/json/close/" + target.id);
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
