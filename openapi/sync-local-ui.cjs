// Synchronize implemented local UI boundaries while retaining the foundation design contracts.
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const root = path.resolve(__dirname, "..");
const YAML = require(
  path.join(root, "runtime/design-review/node/node_modules/yaml"),
);
const python =
  process.env.PYTHON ||
  path.join(
    root,
    process.platform === "win32"
      ? ".venv/Scripts/python.exe"
      : ".venv/bin/python",
  );
const exported = spawnSync(
  python,
  [
    "-c",
    "import json; from agent_cf_server.bootstrap.server import create_app; print(json.dumps(create_app().openapi()))",
  ],
  {
    cwd: root,
    env: { ...process.env, PYTHONPATH: path.join(root, "apps/server/src") },
    encoding: "utf8",
  },
);
if (exported.status !== 0) throw new Error(exported.stderr);
const actual = JSON.parse(exported.stdout);
const file = path.join(root, "openapi/openapi.yaml");
const document = YAML.parseDocument(fs.readFileSync(file, "utf8"));
const selected = [];
for (const [route, methods] of Object.entries(actual.paths)) {
  for (const [method, operation] of Object.entries(methods)) {
    if (
      !operation.tags?.includes("projects") &&
      !route.endsWith("/test") &&
      !["updateSkillDraft", "listSkills", "getSkill", "getRunContext", "createCurrentProcessRun", "createProcessSchedule", "createRobotVersion", "createPairingCode", "createRunnerSession", "pairRunner", "inspectPairingCode", "runnerHeartbeat", "disconnectRunner"].includes(operation.operationId)
    )
      continue;
    const local = structuredClone(operation);
    local.security = [];
    local["x-implementation-status"] = "implemented-local";
    local["x-required-scope"] = "local-operator";
    local.description =
      "Local loopback operator API; remote authentication is pending. Draft save/publication uses revision CAS. Create requests are not deduplicated by Idempotency-Key.";
    if (["getProcessConfiguration", "saveProcessConfiguration", "getCurrentRunContext", "createCurrentProcessRun", "createProcessSchedule", "createRobotVersion"].includes(operation.operationId))
      local.description = "Local loopback operator API; remote authentication is pending. Current Process configuration is saved with expected_token CAS (stale token: 409). Save validates current Skill/model/PC/tool configuration. Process Run creation atomically freezes the current configuration and is deduplicated by Idempotency-Key before creating any snapshot. Web schedules use follow_current_configuration=true. Robot ready_to_use=true saves an immutable usable version atomically; legacy lifecycle APIs remain compatible. No Markdown/ref file upload is required.";
    if (operation.operationId === "cloneProject")
      local.description =
        "Atomically clone all Project configuration, Team, Process versions, Targets including existing counts, and schedules. Preserve lifecycle states and shared catalog references; remap Project/Process/version IDs. Copied schedules are stopped with no execution pointers. Never copy Runs, Logs, artifacts, or ticks. Idempotency-Key deduplicates clone requests and returns 409 if reused with a different name. Local loopback operator API; remote authentication is pending.";
    if (["deleteProject", "deleteProcess"].includes(operation.operationId))
      local.description = "Permanently delete the selected aggregate, including published versions, schedules and completed Run/TaskRun/Attempt history, events and uploaded Server artifacts. Preserve shared catalog entries and PC files. Return {deleted:true}; never silently archive. Reject with 422 while any Run or execution remains unfinished. Keep a deletion audit event. Local loopback operator API; remote authentication is pending.";
    if (["getProject", "updateProjectTeam", "listSkills", "getSkill", "getRunContext"].includes(operation.operationId))
      local.description = operation.description;
    if (operation.operationId === "runnerHeartbeat") {
      local.security = [{ BearerAuth: [] }];
      local["x-required-scope"] = "runner:heartbeat";
      local.description = "Authenticated live Client heartbeat with actual CPU/RAM readings and optional physical memory used/total bytes. Memory used cannot exceed total. Offline presentation hides stale readings; device identity is not changed by a session heartbeat.";
    }
    if (operation.operationId === "createRunnerSession") {
      local.security = [{ BearerAuth: [] }];
      local["x-required-scope"] = "runner:session";
      local.description = "Start authenticated Client session; optional device identity/proof binds an upgraded legacy Client to its existing PC. Reject identity collisions without creating another PC. Reset old telemetry before receiving new samples.";
    }
    if (operation.operationId === "createPairingCode")
      local.description = "Create a one-time pairing code. target_runner_id explicitly reconnects an existing PC in this Workspace, preserving its identity and configuration; omit for a different machine.";
    if (operation.operationId === "pairRunner")
      local.description = "Exchange one-time code and optional device identity/proof. Targeted reconnect preserves PC ID; untargeted known-device reconnect requires the stored device proof. Rotate credential, revoke old sessions, reject unfinished work and never deduplicate by display name. device_key is write-only and only its hash is stored.";
    if (operation.operationId === "disconnectRunner")
      local.description = "Disconnect an idle PC by revoking credential/session while preserving PC identity, configuration and files. Reject unfinished work. Reconnect on the same row restores connectivity without creating another PC.";
    local.parameters ??= [];
    if (
      ["post", "put", "delete"].includes(method) &&
      !local.parameters.some(
        (parameter) => parameter.name === "Idempotency-Key",
      )
    )
      local.parameters.push({
        name: "Idempotency-Key",
        in: "header",
        required: false,
        schema: { type: "string" },
        description:
          "Accepted from Web; create-request deduplication remains pending.",
      });
    document.setIn(["paths", route, method], local);
    selected.push(operation);
  }
}
const used = new Set();
function collect(value) {
  if (!value || typeof value !== "object") return;
  if (value.$ref?.startsWith("#/components/schemas/")) {
    const name = value.$ref.split("/").at(-1);
    if (!used.has(name)) {
      used.add(name);
      collect(actual.components.schemas[name]);
    }
  }
  Object.values(value).forEach(collect);
}
selected.forEach(collect);
for (const name of used)
  if (actual.components.schemas[name])
    document.setIn(
      ["components", "schemas", name],
      actual.components.schemas[name],
    );

const runList = document.getIn(["paths", "/v1/runs", "get"]).toJSON();
runList.parameters = actual.paths["/v1/runs"].get.parameters;
runList.description =
  "Local list in stable created_at/id descending order. Counts exclude pagination. Search matches Run ID. Date bounds use Started or Created when not started, lower inclusive and upper exclusive, normalized to UTC. Running selects queued,running,reconciling,cancelling.";
runList["x-implementation-status"] = "implemented-local";
runList["x-required-scope"] = "local-operator";
runList.security = [];
document.setIn(["paths", "/v1/runs", "get"], runList);
document.setIn(
  ["components", "schemas", "RunPage", "properties", "total_all"],
  {
    type: "integer",
    minimum: 0,
    description: "Total in the selected Project before other filters.",
  },
);
document.setIn(
  ["components", "schemas", "RunPage", "properties", "next_cursor"],
  { type: ["string", "null"] },
);
document.setIn(["components", "schemas", "RuntimeConfig", "properties", "reasoning_effort"], {
  type: ["string", "null"],
  enum: [null, "low", "medium", "high", "xhigh", "max"],
  description: "Optional per-node reasoning level, frozen in each Run snapshot. Omit/null keeps the CLI default. Codex uses model_reasoning_effort; Antigravity supports low/medium/high via --effort. Model support is enforced by the CLI; no global configuration is changed.",
});
fs.writeFileSync(file, document.toString({ lineWidth: 110 }));
console.log(
  JSON.stringify({
    synchronizedLocalOperations: selected.length + 1,
    schemas: used.size,
  }),
);
