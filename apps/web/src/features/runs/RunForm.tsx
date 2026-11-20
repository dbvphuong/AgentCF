import { useEffect, useState } from "react";
import { createProcessRun } from "./api";
import type { Run } from "./types";
import { request, resource } from "../../shared/api";
import type { RecordData } from "../../shared/api";
import { Notice, useResource } from "../../shared/ui";
import { PcPathInput } from "../../shared/PcPathInput";

interface RunFormProps {
  onRunCreated: (run: Run) => void;
  onCancel: () => void;
  initialProcessId?: string;
  embedded?: boolean;
}
export function RunForm({
  onRunCreated,
  onCancel,
  initialProcessId = "",
  embedded = false,
}: RunFormProps) {
  const projects = useResource<RecordData[]>("/v1/projects");
  const [projectId, setProjectId] = useState("");
  const [processes, setProcesses] = useState<RecordData[]>([]);
  const [processId, setProcessId] = useState(initialProcessId);
  const [input, setInput] = useState("{}");
  const [topicDirectory, setTopicDirectory] = useState("");
  const [userRequest, setUserRequest] = useState("");
  const [context, setContext] = useState<RecordData | null>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const runners = useResource<RecordData[]>("/v1/runners");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setContext(null); setTopicDirectory(""); setAdvanced(false); setError("");
    if (!processId) { setContextLoading(false); return; }
    setContextLoading(true);
    request<RecordData>(`/v1/processes/${encodeURIComponent(processId)}/run-context`, "GET", undefined, controller.signal)
      .then(value => { if (!controller.signal.aborted) {setContext(value); setAdvanced(!value.topic_supported);} })
      .catch(e => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setContextLoading(false); });
    return () => controller.abort();
  }, [processId]);
  useEffect(() => {
    const c = new AbortController();
    setProcesses([]);
    if (!initialProcessId) setProcessId("");
    if (projectId)
      request(resource("/v1/projects", projectId), "GET", undefined, c.signal)
        .then((p) =>
          setProcesses(
            p.processes.filter((p: RecordData) => p.status === "active"),
          ),
        )
        .catch((e) => {
          if (!c.signal.aborted) setError(e.message);
        });
    return () => c.abort();
  }, [projectId]);
  return (
    <section className={embedded ? undefined : "run-form-card"}>
      {!embedded && <h2>Chạy Process</h2>}
      {(error || projects.error) && (
        <Notice error>{error || projects.error}</Notice>
      )}
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setError("");
          setLoading(true);
          try {
            if (!advanced && !topicDirectory.trim()) throw new Error("Chọn hoặc nhập đường dẫn thư mục chủ đề.");
            const data = advanced ? JSON.parse(input) : { topic_directory: topicDirectory.trim(), request: userRequest.trim() };
            if (!data || Array.isArray(data) || typeof data !== "object")
              throw new Error("Input phải là JSON object.");
            const run = await createProcessRun(processId, data);
            onRunCreated(run);
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setLoading(false);
          }
        }}
      >
        <fieldset className="form-fields" disabled={loading}>
          {!initialProcessId && (
            <>
              <div className="form-group">
                <label htmlFor="run-project">Project</label>
                <select
                  id="run-project"
                  required
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                >
                  <option value="">Chọn Project…</option>
                  {projects.data
                    ?.filter((p) => p.status === "active")
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="run-process">Process</label>
                <select
                  id="run-process"
                  required
                  value={processId}
                  onChange={(e) => setProcessId(e.target.value)}
                >
                  <option value="">Chọn Process…</option>
                  {processes.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}
          {contextLoading && <Notice>Đang tải cấu hình Process…</Notice>}
          {context?.topic_supported && <>
            <p><strong>{context.process_name}</strong> · PC: {runners.data?.find(r => r.id === context.runner_id)?.name || "PC đã cấu hình"}<br />Thư mục Project: <code>{context.working_directory}</code></p>
            {!advanced && <>
              <div className="form-group">
                <label htmlFor="run-topic">Thư mục chủ đề *</label>
                <PcPathInput id="run-topic" value={topicDirectory} runnerId={context.runner_id} initialDirectory={context.working_directory} directoryOnly onChange={setTopicDirectory}
                  canBrowse={!!runners.data?.some(r => r.id === context.runner_id && ["online", "busy"].includes(r.display_status ?? r.status))} />
              </div>
              <div className="form-group">
                <label htmlFor="run-request">Yêu cầu riêng cho lần chạy (không bắt buộc)</label>
                <textarea id="run-request" rows={3} value={userRequest} onChange={e => setUserRequest(e.target.value)} placeholder="Để trống để các bước làm theo Skill đã chọn." />
              </div>
              <p className="muted">Các bước dùng chung thư mục chủ đề. Kết quả được tạo/sửa trực tiếp trên PC theo Skill.</p>
            </>}
          </>}
          {context && !context.topic_supported && <Notice>{context.reason}</Notice>}
          {context?.topic_supported && <label style={{ display: "flex", alignItems: "center", gap: 8 }}><input type="checkbox" checked={advanced} onChange={e => setAdvanced(e.target.checked)} /> Nhập dữ liệu JSON nâng cao thay cho chủ đề</label>}
          {advanced && <div className="form-group">
            <label htmlFor="run-input">Input JSON</label>
            <textarea
              id="run-input"
              rows={8}
              required
              value={input}
              spellCheck={false}
              onChange={(e) => setInput(e.target.value)}
            />
          </div>}
        </fieldset>
        <div className="form-actions">
          <button
            className="btn btn-outline"
            type="button"
            disabled={loading}
            onClick={onCancel}
          >
            Hủy
          </button>
          <button className="btn btn-primary" disabled={loading || !processId || contextLoading || !context}>
            {loading ? "Đang tạo…" : "Chạy Process"}
          </button>
        </div>
      </form>
    </section>
  );
}
