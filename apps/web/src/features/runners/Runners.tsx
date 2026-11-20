import { useEffect, useState } from "react";
import {
  Confirm,
  EntityForm,
  Modal,
  Notice,
  PageHead,
  useResource,
} from "../../shared/ui";
import { dateTime, request, resource } from "../../shared/api";
import type { RecordData } from "../../shared/api";
import { ConnectPc } from "./ConnectPc";
import { TechnicalDetails } from "../../shared/TechnicalDetails";

export function Runners() {
  const runners = useResource<RecordData[]>("/v1/runners");
  const workspaces = useResource<RecordData[]>("/v1/workspaces");
  const agents = useResource<RecordData[]>("/v1/agents");
  const [connect, setConnect] = useState(false);
  const [connectRunner, setConnectRunner] = useState<RecordData | null>(null);
  const [detailId, setDetailId] = useState("");
  const [action, setAction] = useState<RecordData | null>(null);
  const [disconnecting, setDisconnecting] = useState<RecordData | null>(null);
  const [editing, setEditing] = useState<RecordData | null>(null);
  const [search, setSearch] = useState("");
  const detail = runners.data?.find((r) => r.id === detailId);
  useEffect(() => {
    const id = setInterval(() => { if (!document.hidden) runners.reload(); }, 5000);
    return () => clearInterval(id);
  }, []);
  return (
    <>
      <PageHead title="PC">
        <button
          className="btn btn-primary"
          onClick={() => {
            setConnectRunner(null);
            setConnect(true);
          }}
        >
          + Connect PC
        </button>
      </PageHead>
      <section className="panel">
        <div className="toolbar">
          <input
            aria-label="Tìm PC"
            placeholder="Tìm PC…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button className="btn btn-outline" onClick={runners.reload}>
            Làm mới
          </button>
        </div>
        {runners.error && <Notice error>{runners.error}</Notice>}
        {runners.loading && !runners.data ? (
          <Notice>Đang tải…</Notice>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>PC</th>
                  <th>Hệ điều hành</th>
                  <th>Trạng thái</th>
                  <th>Current run</th>
                  <th>CPU</th>
                  <th>RAM</th>
                  <th>Last seen</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {runners.data
                  ?.filter((r) =>
                    r.name.toLowerCase().includes(search.toLowerCase()),
                  )
                  .map((r) => {
                    const status = r.display_status ?? r.status;
                    return (
                      <tr key={r.id}>
                        <td>
                          <button
                            className="link-button"
                            onClick={() => setDetailId(r.id)}
                          >
                            {r.name}
                          </button>
                          <small className="cell-note">
                            {r.client_version || "—"}
                          </small>
                        </td>
                        <td>{r.os_name || "—"}</td>
                        <td>
                          <span
                            tabIndex={0}
                            className={`badge badge-${status}`}
                            title={r.current_tasks
                              ?.map(
                                (t: RecordData) =>
                                  `${t.process_name} · ${t.node_name ?? "Bước đang chạy"} · Agent điều phối ${agents.data?.find(a => a.id === t.agent_id)?.name ?? "Chưa rõ"}`,
                              )
                              .join("\n")}
                          >
                            {status}
                          </span>
                        </td>
                        <td>
                          {r.current_tasks?.length
                            ? r.current_tasks.map((task: RecordData) => (
                                <a
                                  className="cell-note"
                                  key={task.task_run_id}
                                  href={`#runs/${encodeURIComponent(task.run_id)}`}
                                >
                                  {task.process_name}
                                </a>
                              ))
                            : "—"}
                        </td>
                        <td>
                          {status === "offline" || r.cpu_percent == null
                            ? "—"
                            : `${r.cpu_percent}%`}
                        </td>
                        <td>
                          {status === "offline" || r.ram_percent == null
                            ? "—"
                            : <>{r.ram_percent}%{r.memory_total_bytes && r.memory_used_bytes != null && <small className="cell-note">{(r.memory_used_bytes / 1073741824).toFixed(1)} / {(r.memory_total_bytes / 1073741824).toFixed(1)} GB</small>}</>}
                        </td>
                        <td>{dateTime(r.last_seen_at)}</td>
                        <td>
                          <div className="row-actions">
                            {["online", "busy"].includes(status) ? (
                              <button type="button" className="btn btn-outline btn-sm" onClick={() => setDisconnecting(r)}>Hủy kết nối</button>
                            ) : (
                              <button type="button" className="btn btn-outline btn-sm" onClick={() => { setConnectRunner(r); setConnect(true); }}>Kết nối</button>
                            )}
                            <button
                              className="btn btn-outline btn-sm"
                              onClick={() => setEditing(r)}
                            >
                              Sửa
                            </button>
                            <button
                              className="btn btn-danger btn-sm"
                              onClick={() => setAction(r)}
                            >
                              Xóa
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                {!runners.data?.length && (
                  <tr>
                    <td colSpan={8} className="empty-state">
                      Chưa có PC. Connect để ghép nối Client.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {connect && (
        <ConnectPc
          initialRunner={connectRunner}
          existingRunners={runners.data ?? []}
          onClose={() => {
            setConnect(false);
            setConnectRunner(null);
            runners.reload();
          }}
          onConnected={() => {
            setConnect(false);
            setConnectRunner(null);
            runners.reload();
          }}
        />
      )}
      {detail && (
        <Modal title={detail.name} onClose={() => setDetailId("")}>
          <dl className="detail-grid">
            <div><dt>Workspace</dt><dd>{workspaces.data?.find(w => w.id === detail.workspace_id)?.name || "Không có tên Workspace"}</dd></div>
            <div><dt>Trạng thái</dt><dd>{detail.display_status || detail.status}</dd></div>
            <div><dt>Phiên bản Client</dt><dd>{detail.client_version || "—"}</dd></div>
          </dl>
          <div style={{ margin: "16px 0", display: "flex", gap: "10px" }}>
            <button
              type="button"
              className="btn btn-primary"
              style={{ flex: 1, minHeight: "38px" }}
              onClick={() => {
                const target = detail;
                setDetailId("");
                setConnectRunner(target);
                setConnect(true);
              }}
            >
              ⚡ Kết nối CF Client cho PC này
            </button>
          </div>
          <TechnicalDetails values={{ "PC ID": detail.id, "Workspace ID": detail.workspace_id, "Machine fingerprint": detail.machine_fingerprint }} />
          <p>Last seen: {dateTime(detail.last_seen_at)}</p>
          <h3>TaskRun hiện tại</h3>
          {detail.current_tasks?.length ? (
            detail.current_tasks.map((task: RecordData) => (
              <article className="version-card" key={task.task_run_id}>
                <strong>
                  {task.process_name} · {task.node_name || "Bước đang chạy"}
                </strong>
                <p>Agent điều phối: {agents.data?.find(a => a.id === task.agent_id)?.name || "Không có tên Agent điều phối"}</p>
                <a href={`#runs/${encodeURIComponent(task.run_id)}`}>
                  Xem lần chạy
                </a>
                <small className="cell-note">{task.status}</small>
                <TechnicalDetails values={{ "TaskRun ID": task.task_run_id, "Run ID": task.run_id, "Agent ID": task.agent_id }} />
              </article>
            ))
          ) : (
            <p className="muted">
              Không có TaskRun đang thực thi được Server ghi nhận.
            </p>
          )}
        </Modal>
      )}
      {action && (
        <Confirm
          title={`Xóa PC “${action.name}”?`}
          confirmLabel="Xóa PC"
          onClose={() => setAction(null)}
          onConfirm={async () => {
            await request(
              resource("/v1/runners", action.id),
              "DELETE",
            );
            if (detailId === action.id) setDetailId("");
            runners.reload();
          }}
        >
          PC sẽ được gỡ khỏi danh sách và ngắt kết nối với Agent CF. File trên PC và lịch sử chạy được giữ nguyên.
          Không thể xóa khi PC còn liên quan đến lượt chạy chưa kết thúc. Muốn dùng lại cần Connect PC để ghép nối mới.
        </Confirm>
      )}
      {disconnecting && <Confirm title={`Hủy kết nối “${disconnecting.name}”?`} confirmLabel="Hủy kết nối" onClose={() => setDisconnecting(null)} onConfirm={async () => {
        await request(`${resource('/v1/runners',disconnecting.id)}/disconnect`, 'POST');
        runners.reload();
      }}>Ngắt phiên Client và thu hồi kết nối hiện tại. PC, Skill, cấu hình và file vẫn được giữ. Khi cần dùng lại, bấm Kết nối tại chính dòng này. Nếu còn Run chưa kết thúc, cần dừng Run trước.</Confirm>}
      {editing && <Modal title="Sửa PC" onClose={() => setEditing(null)}>
        <EntityForm initial={editing} fields={[{ key: "name", label: "Tên PC", required: true }]}
          onCancel={() => setEditing(null)} onSave={async data => {
            await request(resource("/v1/runners", editing.id), "PATCH", data);
            setEditing(null); runners.reload();
          }} />
      </Modal>}
    </>
  );
}
