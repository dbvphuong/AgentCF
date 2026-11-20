import { useState } from "react";
import { dateTime, request, resource } from "../../../shared/api";
import type { RecordData } from "../../../shared/api";
import { TechnicalDetails } from "../../../shared/TechnicalDetails";
import {
  Confirm,
  EntityForm,
  Modal,
  Notice,
  useResource,
} from "../../../shared/ui";

export function Schedules({
  process,
  projectId,
  onClose,
}: {
  process: RecordData;
  projectId: string;
  onClose: () => void;
}) {
  const path = `${resource("/v1/processes", process.id)}/schedules`;
  const schedules = useResource<{ items: RecordData[] }>(path);
  const runners = useResource<RecordData[]>("/v1/runners");
  const [create, setCreate] = useState(false);
  const [action, setAction] = useState<RecordData | null>(null);
  return (
    <Modal title={`Schedule · ${process.name}`} onClose={onClose}>
      {[schedules.error, runners.error]
        .filter(Boolean)
        .map((e, i) => (
          <Notice error key={i}>
            {e}
          </Notice>
        ))}
      <button className="btn btn-primary" onClick={() => setCreate(true)}>
        + Schedule
      </button>
      <div className="version-list">
        {schedules.data?.items.map((s) => (
          <article className="version-card" key={s.id}>
            <div className="section-heading">
              <strong>{s.name}</strong>
              <span className="badge">
                {s.is_active ? "Started" : "Stopped"}
              </span>
              <button className="btn btn-outline" onClick={() => setAction(s)}>
                {s.is_active ? "Stop" : "Start"}
              </button>
            </div>
            <p>{s.cadence} · Dùng cấu hình Process đã lưu khi đến lịch</p>
            <p>Lần kế tiếp: {dateTime(s.next_run_at)}</p>
            <small>
              PC:{" "}
              {runners.data?.find((r) => r.id === s.default_runner_id)?.name ??
                "Tự động chọn"}
            </small>
            <TechnicalDetails values={{ "Schedule ID": s.id, "PC ID": s.default_runner_id }} />
          </article>
        ))}
      </div>
      {!schedules.loading && !schedules.data?.items.length && (
        <Notice>Chưa có lịch chạy.</Notice>
      )}
      {create && (
        <EntityForm
          fields={[
            { key: "name", label: "Tên lịch", required: true },
            {
              key: "cadence",
              label: "Lặp lại",
              type: "select",
              default: "daily",
              required: true,
              options: [
                { id: "hourly", name: "Mỗi giờ" },
                { id: "daily", name: "Hằng ngày" },
                { id: "weekly", name: "Hằng tuần" },
              ],
            },
            {
              key: "default_runner_id",
              label: "PC (để trống để tự chọn)",
              type: "select",
              options:
                runners.data?.filter((r) => r.status !== "disabled") ?? [],
            },
            { key: "input", label: "Input JSON", type: "json" },
          ]}
          onCancel={() => setCreate(false)}
          onSave={async (data) => {
            await request(
              `${path}?project_id=${encodeURIComponent(projectId)}`,
              "POST",
              { ...data, follow_current_configuration: true, default_runner_id: data.default_runner_id || null },
            );
            setCreate(false);
            schedules.reload();
          }}
        />
      )}
      {action && (
        <Confirm
          title={`${action.is_active ? "Stop" : "Start"} Schedule?`}
          onClose={() => setAction(null)}
          onConfirm={async () => {
            await request(
              `${resource("/v1/schedules", action.id)}/${action.is_active ? "stop" : "start"}`,
              "POST",
            );
            schedules.reload();
          }}
        >
          Start bật lịch từ mốc tiếp theo. Stop chỉ tắt lịch, Run đang chạy vẫn
          tiếp tục. Save không tự Start.
        </Confirm>
      )}
    </Modal>
  );
}
