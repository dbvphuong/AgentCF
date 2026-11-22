import { useState, useMemo, useEffect } from "react";
import { request } from "../../shared/api";
import { Modal, Notice, useResource } from "../../shared/ui";

interface AiToolModel {
  id: string;
  tool_id: "codex" | "antigravity";
  name: string;
  model_identifier: string;
  status: "active" | "disabled";
}

interface ToolDefinition {
  id: "codex" | "antigravity";
  name: string;
  badge: string;
}

const TOOLS: ToolDefinition[] = [
  {
    id: "codex",
    name: "Codex CLI",
    badge: "OpenAI",
  },
  {
    id: "antigravity",
    name: "Antigravity",
    badge: "Google Antigravity",
  },
];

interface ModelQuota {
  quota_percent: number;
  label: string;
  tier: string;
}

interface CheckResultItem {
  installed: boolean;
  version?: string;
  status: string;
  error?: string;
  executable?: string;
  quota_percent?: number;
  models_count?: number;
  recommended_models?: string[];
  model_quotas?: Record<string, ModelQuota>;
}

export function AiTools() {
  const { data: models, reload, loading } = useResource<AiToolModel[]>("/v1/settings/ai-tool-models");
  const [syncNotice, setSyncNotice] = useState<string | null>(null);
  const [checkNotice, setCheckNotice] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [checkResult, setCheckResult] = useState<{ codex?: CheckResultItem; antigravity?: CheckResultItem } | null>(null);

  // Auto-load quota & PC status on mount
  useEffect(() => {
    request<{ codex: CheckResultItem; antigravity: CheckResultItem }>(
      "/v1/settings/ai-tool-models/check"
    )
      .then(setCheckResult)
      .catch(() => {});
  }, []);

  // Modal configuration
  const [modalToolId, setModalToolId] = useState<"codex" | "antigravity" | null>(null);
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Custom model quick add
  const [customName, setCustomName] = useState("");
  const [customIdentifier, setCustomIdentifier] = useState("");
  const [isAddingCustom, setIsAddingCustom] = useState(false);
  const [customError, setCustomError] = useState<string | null>(null);

  const handleSync = async () => {
    setIsSyncing(true);
    setSyncNotice(null);
    try {
      const res = await request<{
        added_count: number;
        added: string[];
        updated_count?: number;
        removed_count?: number;
        disabled_count?: number;
        total: number;
      }>(
        "/v1/settings/ai-tool-models/sync",
        "POST"
      );
      const changes: string[] = [];
      if (res.added_count > 0) changes.push(`thêm ${res.added_count}`);
      if ((res.updated_count ?? 0) > 0) changes.push(`cập nhật ${res.updated_count}`);
      if ((res.removed_count ?? 0) > 0) changes.push(`gỡ ${res.removed_count} model cũ`);
      if ((res.disabled_count ?? 0) > 0) changes.push(`tắt ${res.disabled_count} model cũ đang có lịch sử`);
      setSyncNotice(
        changes.length > 0
          ? `Đã đồng bộ model thực tế trên máy (${changes.join(", ")}; Tổng: ${res.total} model).`
          : `Đã đồng bộ toàn bộ model mới nhất trên hệ thống (Tổng: ${res.total} model).`
      );
      reload();
      request<{ codex: CheckResultItem; antigravity: CheckResultItem }>(
        "/v1/settings/ai-tool-models/check"
      )
        .then(setCheckResult)
        .catch(() => {});
    } catch (err: unknown) {
      setSyncNotice(`Lỗi đồng bộ model: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleCheck = async () => {
    setIsChecking(true);
    setCheckNotice(null);
    try {
      const res = await request<{ codex: CheckResultItem; antigravity: CheckResultItem }>(
        "/v1/settings/ai-tool-models/check"
      );
      setCheckResult(res);
      const codexMsg = res.codex.installed
        ? `Codex CLI: Sẵn sàng (${res.codex.version || "ok"}, Hạn mức ${res.codex.quota_percent ?? 100}%)`
        : "Codex CLI: Chưa phát hiện trên PC";
      const agyMsg = res.antigravity.installed
        ? `Antigravity: Sẵn sàng (${res.antigravity.version || "ok"}, Hạn mức ${res.antigravity.quota_percent ?? 100}%)`
        : "Antigravity: Chưa phát hiện trên PC";
      setCheckNotice(`Kiểm tra PC hoàn tất: [${codexMsg}] — [${agyMsg}]`);
    } catch (err: unknown) {
      setCheckNotice(`Lỗi kiểm tra PC: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsChecking(false);
    }
  };

  const openModal = (toolId: "codex" | "antigravity") => {
    const currentToolModels = (models ?? []).filter((m) => m.tool_id === toolId);
    const activeIds = currentToolModels.filter((m) => m.status === "active").map((m) => m.id);
    setModalToolId(toolId);
    setSelectedModelIds(activeIds);
    setSearchQuery("");
    setModalError(null);
    setCustomName("");
    setCustomIdentifier("");
    setCustomError(null);
  };

  const closeModal = () => {
    setModalToolId(null);
    setModalError(null);
  };

  const toggleModel = (id: string) => {
    setSelectedModelIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const selectAll = (targetIds: string[]) => {
    setSelectedModelIds((prev) => Array.from(new Set([...prev, ...targetIds])));
  };

  const deselectAll = (targetIds: string[]) => {
    const targetSet = new Set(targetIds);
    setSelectedModelIds((prev) => prev.filter((id) => !targetSet.has(id)));
  };

  const handleSaveConfiguration = async () => {
    if (!modalToolId) return;
    setIsSaving(true);
    setModalError(null);
    try {
      try {
        await request(
          "/v1/settings/ai-tool-models/configure",
          "POST",
          {
            tool_id: modalToolId,
            active_model_ids: selectedModelIds,
          }
        );
      } catch {
        // Fallback for servers running without /configure endpoint
        const targetModels = (models ?? []).filter((m) => m.tool_id === modalToolId);
        await Promise.all(
          targetModels.map((m) => {
            const shouldBeActive = selectedModelIds.includes(m.id);
            const currentActive = m.status === "active";
            if (shouldBeActive !== currentActive) {
              return request(
                `/v1/settings/ai-tool-models/${encodeURIComponent(m.id)}`,
                "PATCH",
                { status: shouldBeActive ? "active" : "disabled" }
              );
            }
            return Promise.resolve();
          })
        );
      }

      const toolName = TOOLS.find((t) => t.id === modalToolId)?.name || modalToolId;
      setActionNotice(`Đã lưu cấu hình ${toolName} (${selectedModelIds.length} model đang bật).`);
      reload();
      closeModal();
    } catch (err: unknown) {
      setModalError(`Lỗi lưu cấu hình: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddCustomModel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalToolId || !customName.trim() || !customIdentifier.trim()) {
      setCustomError("Vui lòng nhập Tên hiển thị và Model ID.");
      return;
    }
    setIsAddingCustom(true);
    setCustomError(null);
    try {
      const generatedId = `cli-${modalToolId}-${customIdentifier.trim().toLowerCase().replace(/[^a-z0-9]/g, "-")}-${Date.now().toString().slice(-4)}`;
      const newModel = await request<AiToolModel>(
        "/v1/settings/ai-tool-models",
        "POST",
        {
          id: generatedId,
          tool_id: modalToolId,
          name: customName.trim(),
          model_identifier: customIdentifier.trim(),
          status: "active",
        }
      );
      setSelectedModelIds((prev) => [...prev, newModel.id]);
      setCustomName("");
      setCustomIdentifier("");
      reload();
    } catch (err: unknown) {
      setCustomError(`Lỗi thêm model: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsAddingCustom(false);
    }
  };

  const currentTool = TOOLS.find((t) => t.id === modalToolId);
  const currentToolModels = useMemo(() => {
    return (models ?? []).filter((m) => m.tool_id === modalToolId);
  }, [models, modalToolId]);

  const filteredModels = useMemo(() => {
    if (!searchQuery.trim()) return currentToolModels;
    const q = searchQuery.toLowerCase();
    return currentToolModels.filter(
      (m) => m.name.toLowerCase().includes(q) || m.model_identifier.toLowerCase().includes(q)
    );
  }, [currentToolModels, searchQuery]);

  // Grouping for clean categorization in modal
  const groupedModels = useMemo(() => {
    if (modalToolId === "codex") {
      const gpt6 = filteredModels.filter((m) => m.model_identifier.startsWith("gpt-6"));
      const gpt5 = filteredModels.filter(
        (m) =>
          m.model_identifier.startsWith("gpt-5") ||
          m.model_identifier.includes("reserve") ||
          m.model_identifier.includes("review")
      );
      const others = filteredModels.filter(
        (m) => !gpt6.includes(m) && !gpt5.includes(m)
      );
      return [
        { label: "Dòng GPT-6 (Khuyên dùng)", items: gpt6 },
        { label: "Dòng GPT-5", items: gpt5 },
        ...(others.length > 0 ? [{ label: "Model tùy biến / Khác", items: others }] : []),
      ];
    } else if (modalToolId === "antigravity") {
      const claude = filteredModels.filter((m) => m.model_identifier.includes("claude"));
      const gemini = filteredModels.filter((m) => m.model_identifier.includes("gemini"));
      const oss = filteredModels.filter((m) => m.model_identifier.includes("gpt-oss"));
      const others = filteredModels.filter(
        (m) => !claude.includes(m) && !gemini.includes(m) && !oss.includes(m)
      );
      return [
        { label: "Dòng Claude (Anthropic)", items: claude },
        { label: "Dòng Gemini (Google)", items: gemini },
        { label: "Mã nguồn mở (Open-Source)", items: oss },
        ...(others.length > 0 ? [{ label: "Model tùy biến / Khác", items: others }] : []),
      ];
    }
    return [{ label: "Tất cả model", items: filteredModels }];
  }, [filteredModels, modalToolId]);

  return (
    <section className="panel">
      {/* 1. Header Toolbar */}
      <div className="toolbar catalog-toolbar" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px", marginBottom: "16px" }}>
        <span style={{ fontWeight: 700, fontSize: "15px", color: "var(--ink)", marginRight: "8px" }}>
          Công cụ AI trên PC
        </span>

        <div style={{ marginLeft: "auto", display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <button
            type="button"
            className="btn btn-outline"
            onClick={handleCheck}
            disabled={isChecking}
            title="Kiểm tra trạng thái cài đặt CLI và hạn mức model trên máy tính"
          >
            {isChecking ? "Đang kiểm tra…" : "Kiểm tra PC"}
          </button>
          <button
            type="button"
            className="btn btn-outline"
            onClick={handleSync}
            disabled={isSyncing}
            title="Đồng bộ tự động các model mới nhất từ hệ thống"
          >
            {isSyncing ? "Đang đồng bộ…" : "Đồng bộ model"}
          </button>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => reload()}
            disabled={loading}
            title="Tải lại danh sách"
          >
            Làm mới
          </button>
        </div>
      </div>

      {syncNotice && <Notice error={syncNotice.startsWith("Lỗi")}>{syncNotice}</Notice>}
      {checkNotice && <Notice error={checkNotice.startsWith("Lỗi")}>{checkNotice}</Notice>}
      {actionNotice && <Notice>{actionNotice}</Notice>}

      {/* 2. Full-Width Table matching Catalog style */}
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th style={{ width: "240px" }}>CÔNG CỤ AI TRÊN PC</th>
              <th style={{ width: "210px" }}>TRẠNG THÁI PC</th>
              <th>MODEL ĐƯỢC CHỌN DÙNG TRONG PROCESS</th>
              <th style={{ width: "130px", textAlign: "right" }}>THAO TÁC</th>
            </tr>
          </thead>
          <tbody>
            {TOOLS.map((tool) => {
              const toolModels = (models ?? []).filter((m) => m.tool_id === tool.id);
              const activeModels = toolModels.filter((m) => m.status === "active");
              const pcInfo = checkResult?.[tool.id];

              return (
                <tr key={tool.id}>
                  {/* Cột 1: Công cụ + Icon */}
                  <td style={{ verticalAlign: "middle" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      {tool.id === "antigravity" ? (
                        <img
                          src="/antigravity-icon.png"
                          alt="Antigravity Logo"
                          style={{
                            width: "36px",
                            height: "36px",
                            borderRadius: "8px",
                            objectFit: "contain",
                            boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
                            flexShrink: 0,
                          }}
                        />
                      ) : (
                        <div
                          style={{
                            width: "36px",
                            height: "36px",
                            borderRadius: "8px",
                            background: "#0f172a",
                            color: "#ffffff",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            flexShrink: 0,
                            boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
                          }}
                        >
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.872zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.6669zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813v6.7227zm1.1448-2.6713l3.056-1.7618 3.056 1.7618v3.5235l-3.056 1.7618-3.056-1.7618z"/>
                          </svg>
                        </div>
                      )}
                      <div>
                        <strong style={{ fontSize: "14px", color: "var(--ink)" }}>{tool.name}</strong>
                        <div>
                          <span
                            style={{
                              fontSize: "11px",
                              fontWeight: 600,
                              padding: "1px 6px",
                              borderRadius: "4px",
                              background: "var(--violet-50)",
                              color: "var(--violet-800)",
                              border: "1px solid var(--violet-200)",
                              display: "inline-block",
                              marginTop: "2px",
                            }}
                          >
                            {tool.badge}
                          </span>
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* Cột 2: Trạng thái PC */}
                  <td style={{ verticalAlign: "middle" }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px", alignItems: "flex-start" }}>
                      {pcInfo ? (
                        pcInfo.installed ? (
                          <>
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "6px",
                                fontSize: "12px",
                                fontWeight: 500,
                                padding: "2px 8px",
                                borderRadius: "12px",
                                background: "var(--success-bg)",
                                color: "var(--success-text)",
                                border: "1px solid var(--success-border)",
                              }}
                              title={pcInfo.executable || ""}
                            >
                              <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10b981" }} />
                              Sẵn sàng {pcInfo.version ? `(${pcInfo.version})` : ""}
                            </span>
                          </>
                        ) : (
                          <span
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "6px",
                              fontSize: "12px",
                              fontWeight: 500,
                              padding: "2px 8px",
                              borderRadius: "12px",
                              background: "var(--danger-bg)",
                              color: "var(--danger-text)",
                              border: "1px solid var(--danger-border)",
                            }}
                          >
                            ✕ Chưa cài đặt
                          </span>
                        )
                      ) : (
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            fontSize: "12px",
                            color: "var(--muted)",
                            padding: "2px 8px",
                            borderRadius: "12px",
                            background: "var(--neutral-bg)",
                            border: "1px solid var(--neutral-border)",
                          }}
                        >
                          ○ Chưa kiểm tra
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Cột 3: Model được chọn */}
                  <td style={{ verticalAlign: "middle" }}>
                    <div style={{ marginBottom: "6px" }}>
                      <span
                        style={{
                          display: "inline-block",
                          fontSize: "11px",
                          fontWeight: 700,
                          letterSpacing: "0.5px",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          background: activeModels.length > 0 ? "rgba(16, 185, 129, 0.12)" : "rgba(239, 68, 68, 0.1)",
                          color: activeModels.length > 0 ? "#059669" : "#dc2626",
                        }}
                      >
                        ĐANG BẬT {activeModels.length} / {toolModels.length} MODEL
                      </span>
                    </div>

                    {activeModels.length > 0 ? (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                        {activeModels.slice(0, 10).map((m) => (
                          <span
                            key={m.id}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "5px",
                              background: "var(--violet-50)",
                              color: "var(--violet-950)",
                              border: "1px solid var(--violet-200)",
                              borderRadius: "6px",
                              padding: "2px 8px",
                              fontSize: "12px",
                              fontWeight: 500,
                            }}
                          >
                            <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: "#10b981" }} />
                            {m.name}
                          </span>
                        ))}
                        {activeModels.length > 10 && (
                          <button
                            type="button"
                            onClick={() => openModal(tool.id)}
                            style={{
                              background: "transparent",
                              border: "1px dashed var(--line-strong)",
                              color: "var(--violet-700)",
                              borderRadius: "6px",
                              padding: "2px 8px",
                              fontSize: "12px",
                              fontWeight: 600,
                              cursor: "pointer",
                            }}
                          >
                            +{activeModels.length - 10} model khác…
                          </button>
                        )}
                      </div>
                    ) : (
                      <div style={{ fontSize: "12px", color: "var(--muted)", fontStyle: "italic" }}>
                        Chưa chọn model nào (bấm "Chọn model" để kích hoạt)
                      </div>
                    )}
                  </td>

                  {/* Cột 4: Thao tác */}
                  <td style={{ textAlign: "right", verticalAlign: "middle" }}>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => openModal(tool.id)}
                      style={{ whiteSpace: "nowrap" }}
                    >
                      Chọn model
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* 3. Multi-Select Model Checklist Modal */}
      {modalToolId && currentTool && (
        <Modal
          title={`Cấu hình model cho ${currentTool.name}`}
          onClose={closeModal}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", paddingBottom: "2px" }}>
              {currentTool.id === "antigravity" ? (
                <img
                  src="/antigravity-icon.png"
                  alt="Antigravity"
                  style={{ width: "28px", height: "28px", borderRadius: "6px", objectFit: "contain" }}
                />
              ) : (
                <div
                  style={{
                    width: "28px",
                    height: "28px",
                    borderRadius: "6px",
                    background: "#0f172a",
                    color: "#ffffff",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.872zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.6669zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813v6.7227zm1.1448-2.6713l3.056-1.7618 3.056 1.7618v3.5235l-3.056 1.7618-3.056-1.7618z"/>
                  </svg>
                </div>
              )}
              <span style={{ fontWeight: 700, fontSize: "14px", color: "var(--ink)" }}>{currentTool.name}</span>
            </div>

            {modalError && <Notice error>{modalError}</Notice>}

            {/* Quick Actions & Search Bar */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "8px",
                background: "var(--violet-50)",
                padding: "8px 12px",
                borderRadius: "8px",
                border: "1px solid var(--violet-200)",
              }}
            >
              <div style={{ display: "flex", gap: "6px" }}>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ padding: "4px 10px", fontSize: "12px" }}
                  onClick={() => selectAll(filteredModels.map((m) => m.id))}
                >
                  Chọn tất cả {filteredModels.length < currentToolModels.length ? `(${filteredModels.length})` : ""}
                </button>
                <button
                  type="button"
                  className="btn btn-outline"
                  style={{ padding: "4px 10px", fontSize: "12px" }}
                  onClick={() => deselectAll(filteredModels.map((m) => m.id))}
                >
                  Bỏ chọn tất cả
                </button>
              </div>

              <div style={{ fontWeight: 600, fontSize: "13px", color: "var(--violet-950)" }}>
                Đã chọn: {selectedModelIds.length} / {currentToolModels.length}
              </div>
            </div>

            {/* Search Input */}
            <div>
              <input
                type="search"
                placeholder="Tìm model theo tên hoặc model ID…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: "6px",
                  border: "1px solid var(--line)",
                  fontSize: "13px",
                }}
              />
            </div>

            {/* Categorized Checkbox List */}
            <div
              style={{
                maxHeight: "380px",
                overflowY: "auto",
                border: "1px solid var(--line)",
                borderRadius: "8px",
                padding: "8px 12px",
                background: "#fafafa",
              }}
            >
              {groupedModels.every((g) => g.items.length === 0) ? (
                <div style={{ padding: "24px", textAlign: "center", color: "var(--muted)", fontSize: "13px" }}>
                  Không tìm thấy model nào khớp với từ khóa.
                </div>
              ) : (
                groupedModels.map(
                  (group) =>
                    group.items.length > 0 && (
                      <div key={group.label} style={{ marginBottom: "14px" }}>
                        <div
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            textTransform: "uppercase",
                            letterSpacing: "0.06em",
                            color: "var(--subtle)",
                            padding: "4px 4px 6px",
                          }}
                        >
                          {group.label}
                        </div>

                        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          {group.items.map((m) => {
                            const isChecked = selectedModelIds.includes(m.id);

                            return (
                              <label
                                key={m.id}
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "space-between",
                                  padding: "8px 12px",
                                  borderRadius: "6px",
                                  border: "1px solid",
                                  borderColor: isChecked ? "var(--violet-200)" : "transparent",
                                  background: isChecked ? "#ffffff" : "transparent",
                                  cursor: "pointer",
                                  transition: "all 0.15s ease",
                                }}
                              >
                                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                  <input
                                    type="checkbox"
                                    checked={isChecked}
                                    onChange={() => toggleModel(m.id)}
                                    style={{
                                      accentColor: "var(--violet-700)",
                                      width: "16px",
                                      height: "16px",
                                      cursor: "pointer",
                                    }}
                                  />
                                  <div>
                                    <span
                                      style={{
                                        fontWeight: 600,
                                        fontSize: "13px",
                                        color: isChecked ? "var(--violet-950)" : "var(--ink)",
                                      }}
                                    >
                                      {m.name}
                                    </span>
                                    <span
                                      style={{
                                        marginLeft: "8px",
                                        fontFamily: "monospace",
                                        fontSize: "11px",
                                        color: "var(--muted)",
                                        background: "rgba(0,0,0,0.04)",
                                        padding: "1px 5px",
                                        borderRadius: "4px",
                                      }}
                                    >
                                      {m.model_identifier}
                                    </span>
                                  </div>
                                </div>

                                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                  <span
                                    style={{
                                      fontSize: "11px",
                                      fontWeight: 500,
                                      padding: "2px 8px",
                                      borderRadius: "10px",
                                      background: isChecked ? "var(--success-bg)" : "var(--neutral-bg)",
                                      color: isChecked ? "var(--success-text)" : "var(--neutral-text)",
                                      border: `1px solid ${isChecked ? "var(--success-border)" : "var(--neutral-border)"}`,
                                    }}
                                  >
                                    {isChecked ? "Bật" : "Tắt"}
                                  </span>
                                </div>
                              </label>
                            );
                          })}
                        </div>
                      </div>
                    )
                )
              )}
            </div>

            {/* Custom Model Addition Accordion */}
            <details
              style={{
                background: "#ffffff",
                border: "1px solid var(--line)",
                borderRadius: "8px",
                padding: "8px 12px",
              }}
            >
              <summary
                style={{
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: "12px",
                  color: "var(--violet-800)",
                }}
              >
                + Thêm model tùy biến cho {currentTool.name}
              </summary>
              <form onSubmit={handleAddCustomModel} style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "8px" }}>
                {customError && <Notice error>{customError}</Notice>}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "11px", marginBottom: "3px", fontWeight: 500 }}>
                      Tên hiển thị:
                    </label>
                    <input
                      type="text"
                      placeholder="Ví dụ: GPT-6.5 Custom"
                      value={customName}
                      onChange={(e) => setCustomName(e.target.value)}
                      style={{ width: "100%", padding: "6px 8px", borderRadius: "4px", border: "1px solid var(--line)", fontSize: "12px" }}
                    />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: "11px", marginBottom: "3px", fontWeight: 500 }}>
                      Model ID gửi tới CLI:
                    </label>
                    <input
                      type="text"
                      placeholder="Ví dụ: gpt-6.5-custom"
                      value={customIdentifier}
                      onChange={(e) => setCustomIdentifier(e.target.value)}
                      style={{ width: "100%", padding: "6px 8px", borderRadius: "4px", border: "1px solid var(--line)", fontSize: "12px" }}
                    />
                  </div>
                </div>
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <button
                    type="submit"
                    className="btn btn-outline"
                    disabled={isAddingCustom}
                    style={{ fontSize: "12px", padding: "4px 10px" }}
                  >
                    {isAddingCustom ? "Đang thêm…" : "Thêm vào danh sách"}
                  </button>
                </div>
              </form>
            </details>

            {/* Modal Actions */}
            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                gap: "8px",
                marginTop: "4px",
                borderTop: "1px solid var(--line)",
                paddingTop: "12px",
              }}
            >
              <button
                type="button"
                className="btn btn-outline"
                onClick={closeModal}
                disabled={isSaving}
              >
                Hủy
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleSaveConfiguration}
                disabled={isSaving}
              >
                {isSaving ? "Đang lưu…" : "Lưu cấu hình"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </section>
  );
}
