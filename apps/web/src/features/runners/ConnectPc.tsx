import { useEffect, useState } from "react";
import { EntityForm, Modal, Notice, useResource } from "../../shared/ui";
import { request, resource, dateTime } from "../../shared/api";
import type { RecordData } from "../../shared/api";

export function ConnectPc({
  onClose,
  onConnected,
  initialRunner,
  existingRunners,
}: {
  onClose: () => void;
  onConnected: () => void;
  initialRunner?: RecordData | null;
  existingRunners?: RecordData[];
}) {
  const workspaces = useResource<RecordData[]>("/v1/workspaces");
  const desktop = useResource<RecordData>("/v1/client/desktop");
  const [pairing, setPairing] = useState<RecordData | null>(null);
  const [state, setState] = useState<RecordData | null>(null);
  const [error, setError] = useState("");

  // Khi có initialRunner (bấm nút kết nối nhanh trên PC có sẵn), tự động tạo mã ghép nối và vào thẳng bước 2
  useEffect(() => {
    if (initialRunner && !pairing && workspaces.data) {
      const wsId = initialRunner.workspace_id || workspaces.data[0]?.id;
      if (wsId) {
        void create({ workspace_id: wsId, name: initialRunner.name, target_runner_id: initialRunner.id }).catch((e) => setError(e.message));
      }
    }
  }, [initialRunner, workspaces.data]);

  useEffect(() => {
    if (!pairing) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const next = await request<RecordData>(resource("/v1/pairing-codes", pairing.id));
        if (cancelled) return;
        setState(next);
        setError("");
        if (next.status === "connected") {
          onConnected();
          return;
        }
        if (["expired", "removed"].includes(next.status)) return;
      } catch (e) {
        if (cancelled) return;
        setError((e as Error).message);
      }
      if (!cancelled) timer = setTimeout(poll, 1500);
    };
    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [pairing?.id]);

  const create = async (data: RecordData) => {
    const result = await request<RecordData>("/v1/pairing-codes", "POST", { ...data, expires_in_seconds: 600 });
    setPairing({ ...result, payload: data });
    setState(null);
  };

  const connected = state?.status === "connected";
  const expired = state?.status === "expired" || state?.status === "removed";
  const link = pairing ? "agentcf://connect/#" + new URLSearchParams({ server: window.location.origin, code: pairing.pairing_code }) : "";
  const currentStep = !pairing ? 1 : connected ? 3 : 2;

  return (
    <Modal title="Kết nối PC Runner (Connect PC)" onClose={onClose}>
      {/* Stepper chỉ số bước trực quan cao cấp */}
      <div className="connect-stepper" aria-label="Các bước kết nối PC">
        <div className={`connect-step ${currentStep === 1 ? "active" : currentStep > 1 ? "done" : ""}`}>
          <span className="step-num">{currentStep > 1 ? "✓" : "1"}</span>
          <span className="step-label">Thông tin PC</span>
        </div>
        <div className={`step-line ${currentStep > 1 ? "done" : ""}`} />
        <div className={`connect-step ${currentStep === 2 ? "active" : currentStep > 2 ? "done" : ""}`}>
          <span className="step-num">{currentStep > 2 ? "✓" : "2"}</span>
          <span className="step-label">Mở CF Client</span>
        </div>
        <div className={`step-line ${currentStep > 2 ? "done" : ""}`} />
        <div className={`connect-step ${currentStep === 3 ? "active" : ""}`}>
          <span className="step-num">{currentStep === 3 ? "✓" : "3"}</span>
          <span className="step-label">Đã kết nối</span>
        </div>
      </div>

      {error && <Notice error>{error}</Notice>}
      {workspaces.error && <Notice error>{workspaces.error}</Notice>}

      {!pairing ? (
        <>
          {/* Danh sách chọn nhanh PC có sẵn - Người dùng KHÔNG cần gõ lại tên! */}
          {existingRunners && existingRunners.length > 0 && (
            <div className="connect-existing-pc-section">
              <span className="existing-pc-label">⚡ Chọn nhanh PC đã có để kết nối ngay:</span>
              <div className="existing-pc-list">
                {existingRunners.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    className="existing-pc-btn"
                    onClick={() => {
                      const wsId = r.workspace_id || workspaces.data?.[0]?.id;
                      if (wsId) void create({ workspace_id: wsId, name: r.name, target_runner_id: r.id }).catch(e => setError(e.message));
                    }}
                  >
                    <span>🖥️</span>
                    <span>Kết nối <strong>{r.name}</strong></span>
                  </button>
                ))}
              </div>
              <div className="connect-divider">
                <span>hoặc thêm định danh PC mới</span>
              </div>
            </div>
          )}

          <div className="connect-info-box">
            <div className="info-icon-badge">🖥️</div>
            <div className="info-text">
              <strong>CF Client Runner</strong>
              <p>Ứng dụng chạy ngầm trên PC để nhận việc và kết nối với Codex/Antigravity. Bạn sẽ mở Client ở bước tiếp theo.</p>
            </div>
          </div>

          <EntityForm
            fields={[
              { key: "workspace_id", label: "Workspace", type: "select", options: workspaces.data ?? [], required: true },
              { key: "name", label: "Tên PC", required: true },
            ]}
            onCancel={onClose}
            submitLabel="Tiếp tục"
            onSave={create}
          />
        </>
      ) : connected ? (
        <div className="connect-success-box">
          <div className="success-icon-pulse">✓</div>
          <Notice>PC “{state.name}” đã kết nối thành công! Client đã mở phiên và gửi heartbeat.</Notice>
          <p className="muted" style={{ margin: "12px 0 18px", fontSize: "13px" }}>
            Client tiếp tục chạy dưới khay hệ thống khi đóng Web/cửa sổ Client. Bạn có thể bật Khởi động cùng Windows trong Client.
          </p>
          <button className="btn btn-primary" style={{ width: "100%", minHeight: "40px" }} onClick={onClose}>
            Hoàn tất
          </button>
        </div>
      ) : (
        <div className="connect-pairing-container">
          <div className="pairing-header-badge">
            <span className="pc-dot-pulse" />
            <span>Đang ghép nối: <strong>{pairing.payload.name}</strong></span>
            <span className="pairing-timer">Hết hạn: {dateTime(pairing.expires_at)}</span>
          </div>

          {expired ? (
            <div style={{ marginTop: "16px" }}>
              <Notice error>Mã đã hết hạn hoặc PC đã bị gỡ. Tạo mã mới để kết nối lại.</Notice>
              <button
                className="btn btn-primary"
                onClick={() => void create(pairing.payload).catch((e) => setError(e.message))}
              >
                Tạo mã mới
              </button>
            </div>
          ) : (
            <>
              <div className="connect-actions-clean">
                <a className="btn btn-primary btn-cta-open" href={link}>
                  <span>⚡</span> Mở CF Client trên máy này
                </a>
                {desktop.data?.installer_available ? (
                  <a className="btn btn-outline btn-cta-download" href="/v1/client/windows-installer" download>
                    <span>📥</span> Tải CF Client cho Windows
                  </a>
                ) : desktop.error ? (
                  <Notice error>{desktop.error}</Notice>
                ) : null}
              </div>

              <div className="connect-status-live">
                <span className="live-radar" />
                <span>{state?.status === "paired" ? "Đã ghép nối; đang chờ Client mở phiên và gửi heartbeat…" : "Đang chờ xác nhận kết nối trong CF Client…"}</span>
              </div>

              <output className="pairing-code" style={{ display: "none" }}>{pairing.pairing_code}</output>
            </>
          )}
        </div>
      )}
    </Modal>
  );
}
