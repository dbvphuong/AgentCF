import { useMemo, useState } from "react";
import { Confirm, Modal, Notice, PageHead, Tabs, useResource } from "../../shared/ui";
import { request, resource } from "../../shared/api";
import type { RecordData } from "../../shared/api";
import { TechnicalDetails } from "../../shared/TechnicalDetails";

interface AgentTemplate {
  id: string;
  name: string;
  description: string;
  prompt_text: string;
  allow_reply: boolean;
  allow_retry: boolean;
  allow_need_human: boolean;
  max_turns: number;
  is_default: boolean;
}

interface AgentFormState {
  id?: string;
  name: string;
  role_id: string;
  model_id: string;
  template_id: string;
  instructions: string;
  allow_reply: boolean;
  allow_retry: boolean;
  allow_need_human: boolean;
  max_turns: number;
  allowed_tool_ids: string[];
}

interface TemplateFormState {
  id?: string;
  name: string;
  description: string;
  prompt_text: string;
  allow_reply: boolean;
  allow_retry: boolean;
  allow_need_human: boolean;
  max_turns: number;
  is_default: boolean;
}

function PermissionPills({
  allowReply,
  allowRetry,
  allowNeedHuman,
  maxTurns,
}: {
  allowReply?: boolean;
  allowRetry?: boolean;
  allowNeedHuman?: boolean;
  maxTurns?: number;
}) {
  return (
    <div className="perm-pills">
      {allowReply !== false && <span className="perm-pill perm-reply">Reply</span>}
      {allowRetry !== false && <span className="perm-pill perm-retry">Retry</span>}
      {allowNeedHuman !== false && <span className="perm-pill perm-human">Hỏi người</span>}
      {allowReply === false && allowRetry === false && allowNeedHuman === false && (
        <span className="perm-pill">Chạy thẳng</span>
      )}
      {typeof maxTurns === "number" && <span className="perm-turns">{maxTurns} lượt</span>}
    </div>
  );
}

export function Agents() {
  const [tab, setTab] = useState("Agent điều phối");
  const agents = useResource<RecordData[]>("/v1/agents");
  const templates = useResource<AgentTemplate[]>("/v1/agent-templates");
  const roles = useResource<RecordData[]>("/v1/settings/roles?status=active");
  const models = useResource<RecordData[]>("/v1/settings/models?status=active");
  const skills = useResource<RecordData[]>("/v1/skills?status=active");
  const tools = useResource<RecordData[]>("/v1/skills/tools?status=active");
  const usage = useResource<RecordData>("/v1/overview/summary");

  const [agentSearch, setAgentSearch] = useState("");
  const [templateSearch, setTemplateSearch] = useState("");
  const [agentForm, setAgentForm] = useState<AgentFormState | null>(null);
  const [templateForm, setTemplateForm] = useState<TemplateFormState | null>(null);
  const [deleteAgentTarget, setDeleteAgentTarget] = useState<RecordData | null>(null);
  const [deleteTemplateTarget, setDeleteTemplateTarget] = useState<AgentTemplate | null>(null);
  const [formError, setFormError] = useState("");
  const [actionError, setActionError] = useState("");
  const [saving, setSaving] = useState(false);

  const templateList = templates.data ?? [];
  const defaultTemplate = useMemo(
    () => templateList.find((t) => t.is_default) ?? templateList[0] ?? null,
    [templateList],
  );

  const openNewAgent = () => {
    setFormError("");
    const tpl = defaultTemplate;
    setAgentForm({
      name: "",
      role_id: roles.data?.[0]?.id ?? "",
      model_id: models.data?.[0]?.id ?? "",
      template_id: tpl?.id ?? "",
      instructions: tpl?.prompt_text ?? "",
      allow_reply: tpl?.allow_reply ?? true,
      allow_retry: tpl?.allow_retry ?? true,
      allow_need_human: tpl?.allow_need_human ?? true,
      max_turns: tpl?.max_turns ?? 10,
      allowed_tool_ids: [],
    });
  };

  const openEditAgent = async (row: RecordData) => {
    setFormError("");
    let detail = row;
    try {
      detail = await request<RecordData>(resource("/v1/agents", row.id));
    } catch {
      /* fallback to row */
    }
    setAgentForm({
      id: detail.id,
      name: detail.name ?? "",
      role_id: detail.role_id ?? "",
      model_id: detail.model_id ?? "",
      template_id: detail.template_id ?? "",
      instructions: detail.instructions ?? "",
      allow_reply: detail.allow_reply ?? true,
      allow_retry: detail.allow_retry ?? true,
      allow_need_human: detail.allow_need_human ?? true,
      max_turns: detail.max_turns ?? 10,
      allowed_tool_ids: detail.allowed_tool_ids ?? [],
    });
  };

  const applyTemplateToAgentForm = (templateId: string, onlyUpdateSelect = false) => {
    if (!agentForm) return;
    const tpl = templateList.find((t) => t.id === templateId);
    if (!tpl || onlyUpdateSelect) {
      setAgentForm({ ...agentForm, template_id: templateId });
      return;
    }
    setAgentForm({
      ...agentForm,
      template_id: tpl.id,
      instructions: tpl.prompt_text,
      allow_reply: tpl.allow_reply,
      allow_retry: tpl.allow_retry,
      allow_need_human: tpl.allow_need_human,
      max_turns: tpl.max_turns,
    });
  };

  const handleSaveAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agentForm) return;
    if (!agentForm.name.trim() || !agentForm.role_id || !agentForm.model_id) {
      setFormError("Vui lòng nhập Tên, Role và Model API.");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      const payload = {
        name: agentForm.name.trim(),
        role_id: agentForm.role_id,
        model_id: agentForm.model_id,
        template_id: agentForm.template_id || null,
        instructions: agentForm.instructions,
        allow_reply: agentForm.allow_reply,
        allow_retry: agentForm.allow_retry,
        allow_need_human: agentForm.allow_need_human,
        max_turns: Math.max(1, Math.min(50, Number(agentForm.max_turns) || 10)),
        allowed_tool_ids: agentForm.allowed_tool_ids,
      };
      if (agentForm.id) {
        await request(resource("/v1/agents", agentForm.id), "PATCH", payload);
      } else {
        await request("/v1/agents", "POST", { id: crypto.randomUUID(), ...payload });
      }
      setAgentForm(null);
      agents.reload();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Không lưu được Agent.");
    } finally {
      setSaving(false);
    }
  };

  const openNewTemplate = () => {
    setFormError("");
    setTemplateForm({
      name: "",
      description: "",
      prompt_text: defaultTemplate?.prompt_text ?? "",
      allow_reply: true,
      allow_retry: true,
      allow_need_human: true,
      max_turns: 10,
      is_default: templateList.length === 0,
    });
  };

  const openEditTemplate = (tpl: AgentTemplate) => {
    setFormError("");
    setTemplateForm({ ...tpl });
  };

  const handleSaveTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!templateForm) return;
    if (!templateForm.name.trim() || !templateForm.prompt_text.trim()) {
      setFormError("Vui lòng nhập Tên mẫu và Nội dung Prompt.");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      const payload = {
        name: templateForm.name.trim(),
        description: templateForm.description.trim(),
        prompt_text: templateForm.prompt_text.trim(),
        allow_reply: templateForm.allow_reply,
        allow_retry: templateForm.allow_retry,
        allow_need_human: templateForm.allow_need_human,
        max_turns: Math.max(1, Math.min(50, Number(templateForm.max_turns) || 10)),
        is_default: templateForm.is_default,
      };
      if (templateForm.id) {
        await request(resource("/v1/agent-templates", templateForm.id), "PATCH", payload);
      } else {
        await request("/v1/agent-templates", "POST", payload);
      }
      setTemplateForm(null);
      templates.reload();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Không lưu được mẫu điều phối.");
    } finally {
      setSaving(false);
    }
  };

  const handleSetDefaultTemplate = async (tpl: AgentTemplate) => {
    setActionError("");
    try {
      await request(`${resource("/v1/agent-templates", tpl.id)}/default`, "POST", {});
      templates.reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Không đặt được mẫu mặc định.");
    }
  };

  const agentRows = (agents.data ?? []).filter(
    (row) =>
      row.status !== "archived" &&
      `${row.name} ${row.role_name ?? ""} ${row.model_name ?? ""}`
        .toLowerCase()
        .includes(agentSearch.toLowerCase()),
  );

  const filteredTemplates = templateList.filter((tpl) =>
    `${tpl.name} ${tpl.description}`.toLowerCase().includes(templateSearch.toLowerCase()),
  );

  return (
    <>
      <PageHead title="Agent điều phối" />
      <Tabs items={["Agent điều phối", "Mẫu điều phối"]} value={tab} onChange={setTab} />
      {[agents, templates, roles, models, skills, tools, usage]
        .filter((r) => r.error)
        .map((r, i) => (
          <Notice key={i} error>
            {r.error}
          </Notice>
        ))}
      {actionError && <Notice error>{actionError}</Notice>}

      {tab === "Agent điều phối" ? (
        <section className="panel">
          <div className="toolbar catalog-toolbar">
            <input
              aria-label="Tìm Agent điều phối"
              placeholder="Tìm theo tên, role, model…"
              value={agentSearch}
              onChange={(e) => setAgentSearch(e.target.value)}
            />
            <button type="button" className="btn btn-outline" onClick={agents.reload}>
              Làm mới
            </button>
            <button
              type="button"
              className="btn btn-primary"
              style={{ marginLeft: "auto" }}
              onClick={openNewAgent}
            >
              + Thêm Agent
            </button>
          </div>
          {agents.loading ? (
            <Notice>Đang tải…</Notice>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Tên</th>
                    <th>Role</th>
                    <th>Model API</th>
                    <th>Quyền điều phối</th>
                    <th>Skills</th>
                    <th>Tokens tháng</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {agentRows.map((row) => {
                    const item = usage.data?.agents_token_usage?.find(
                      (a: RecordData) => a.agent_id === row.id,
                    );
                    const skillText =
                      row.skill_ids
                        ?.map(
                          (id: string) =>
                            skills.data?.find((s) => s.id === id)?.name ?? "Skill",
                        )
                        .join(", ") || "—";
                    return (
                      <tr key={row.id}>
                        <td>
                          <strong>{row.name}</strong>
                          <TechnicalDetails values={{ ID: row.id }} />
                        </td>
                        <td>{row.role_name}</td>
                        <td>{row.model_name}</td>
                        <td>
                          <PermissionPills
                            allowReply={row.allow_reply}
                            allowRetry={row.allow_retry}
                            allowNeedHuman={row.allow_need_human}
                            maxTurns={row.max_turns}
                          />
                        </td>
                        <td>{skillText}</td>
                        <td>
                          {item?.total_tokens == null
                            ? "—"
                            : Number(item.total_tokens).toLocaleString("vi-VN")}
                        </td>
                        <td>
                          <div className="row-actions">
                            <button
                              type="button"
                              className="btn btn-outline btn-sm"
                              onClick={() => openEditAgent(row)}
                            >
                              Sửa
                            </button>
                            <button
                              type="button"
                              className="btn btn-danger btn-sm"
                              onClick={() => setDeleteAgentTarget(row)}
                            >
                              Xóa
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  {!agentRows.length && (
                    <tr>
                      <td colSpan={7} className="empty-state">
                        Chưa có Agent điều phối nào.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : (
        <section className="panel">
          <div className="toolbar catalog-toolbar">
            <input
              aria-label="Tìm mẫu điều phối"
              placeholder="Tìm mẫu theo tên hoặc mô tả…"
              value={templateSearch}
              onChange={(e) => setTemplateSearch(e.target.value)}
            />
            <button type="button" className="btn btn-outline" onClick={templates.reload}>
              Làm mới
            </button>
            <button
              type="button"
              className="btn btn-primary"
              style={{ marginLeft: "auto" }}
              onClick={openNewTemplate}
            >
              + Thêm mẫu
            </button>
          </div>
          {templates.loading ? (
            <Notice>Đang tải…</Notice>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Tên mẫu</th>
                    <th>Mô tả</th>
                    <th>Quyền điều phối</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTemplates.map((tpl) => (
                    <tr key={tpl.id}>
                      <td>
                        <div className="template-name-cell">
                          <strong>{tpl.name}</strong>
                          {tpl.is_default && <span className="badge-default">Mặc định</span>}
                        </div>
                      </td>
                      <td>{tpl.description || "—"}</td>
                      <td>
                        <PermissionPills
                          allowReply={tpl.allow_reply}
                          allowRetry={tpl.allow_retry}
                          allowNeedHuman={tpl.allow_need_human}
                          maxTurns={tpl.max_turns}
                        />
                      </td>
                      <td>
                        <div className="row-actions">
                          {!tpl.is_default && (
                            <button
                              type="button"
                              className="btn btn-outline btn-sm"
                              onClick={() => handleSetDefaultTemplate(tpl)}
                            >
                              Đặt mặc định
                            </button>
                          )}
                          <button
                            type="button"
                            className="btn btn-outline btn-sm"
                            onClick={() => openEditTemplate(tpl)}
                          >
                            Sửa
                          </button>
                          {!tpl.is_default && (
                            <button
                              type="button"
                              className="btn btn-danger btn-sm"
                              onClick={() => setDeleteTemplateTarget(tpl)}
                            >
                              Xóa
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!filteredTemplates.length && (
                    <tr>
                      <td colSpan={4} className="empty-state">
                        Chưa có mẫu điều phối nào.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {agentForm && (
        <Modal
          title={agentForm.id ? "Sửa Agent điều phối" : "Thêm Agent điều phối"}
          onClose={() => setAgentForm(null)}
        >
          <form onSubmit={handleSaveAgent}>
            {formError && <Notice error>{formError}</Notice>}
            <fieldset disabled={saving} className="form-fields">
              <div className="form-grid-2">
                <div className="form-group">
                  <label htmlFor="agent-name">Tên *</label>
                  <input
                    id="agent-name"
                    value={agentForm.name}
                    onChange={(e) => setAgentForm({ ...agentForm, name: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="agent-role">Role *</label>
                  <select
                    id="agent-role"
                    value={agentForm.role_id}
                    onChange={(e) => setAgentForm({ ...agentForm, role_id: e.target.value })}
                    required
                  >
                    <option value="">Chọn Role…</option>
                    {(roles.data ?? []).map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-grid-2">
                <div className="form-group">
                  <label htmlFor="agent-model">Model API *</label>
                  <select
                    id="agent-model"
                    value={agentForm.model_id}
                    onChange={(e) => setAgentForm({ ...agentForm, model_id: e.target.value })}
                    required
                  >
                    <option value="">Chọn Model API…</option>
                    {(models.data ?? []).map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="agent-template">Mẫu điều phối</label>
                  <div className="template-select-row">
                    <select
                      id="agent-template"
                      value={agentForm.template_id}
                      onChange={(e) =>
                        applyTemplateToAgentForm(e.target.value, Boolean(agentForm.id))
                      }
                    >
                      <option value="">Tùy chỉnh riêng</option>
                      {templateList.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                          {t.is_default ? " (Mặc định)" : ""}
                        </option>
                      ))}
                    </select>
                    {agentForm.id && agentForm.template_id && (
                      <button
                        type="button"
                        className="btn btn-outline btn-sm"
                        onClick={() => applyTemplateToAgentForm(agentForm.template_id, false)}
                      >
                        Nạp mẫu
                      </button>
                    )}
                  </div>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="agent-prompt">Hướng dẫn điều phối (Prompt)</label>
                <textarea
                  id="agent-prompt"
                  rows={6}
                  value={agentForm.instructions}
                  onChange={(e) =>
                    setAgentForm({ ...agentForm, instructions: e.target.value })
                  }
                />
              </div>

              <div className="form-group">
                <label>Quyền xử lý khi chạy</label>
                <div className="perm-row">
                  <label className="perm-check">
                    <input
                      type="checkbox"
                      checked={agentForm.allow_reply}
                      onChange={(e) =>
                        setAgentForm({ ...agentForm, allow_reply: e.target.checked })
                      }
                    />
                    Tự trả lời (Reply)
                  </label>
                  <label className="perm-check">
                    <input
                      type="checkbox"
                      checked={agentForm.allow_retry}
                      onChange={(e) =>
                        setAgentForm({ ...agentForm, allow_retry: e.target.checked })
                      }
                    />
                    Thử lại (Retry)
                  </label>
                  <label className="perm-check">
                    <input
                      type="checkbox"
                      checked={agentForm.allow_need_human}
                      onChange={(e) =>
                        setAgentForm({ ...agentForm, allow_need_human: e.target.checked })
                      }
                    />
                    Hỏi người (Need Human)
                  </label>
                  <label className="perm-turns-input">
                    Tối đa
                    <input
                      type="number"
                      min={1}
                      max={50}
                      value={agentForm.max_turns}
                      onChange={(e) =>
                        setAgentForm({
                          ...agentForm,
                          max_turns: Number(e.target.value) || 10,
                        })
                      }
                    />
                    lượt
                  </label>
                </div>
              </div>

              {(tools.data ?? []).length > 0 && (
                <div className="form-group">
                  <label>Allowed tools</label>
                  <div className="perm-row">
                    {(tools.data ?? []).map((t) => {
                      const checked = agentForm.allowed_tool_ids.includes(t.id);
                      return (
                        <label key={t.id} className="perm-check">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(e) => {
                              const next = e.target.checked
                                ? [...agentForm.allowed_tool_ids, t.id]
                                : agentForm.allowed_tool_ids.filter((id) => id !== t.id);
                              setAgentForm({ ...agentForm, allowed_tool_ids: next });
                            }}
                          />
                          {t.name}
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}
            </fieldset>
            <div className="dialog-actions">
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setAgentForm(null)}
                disabled={saving}
              >
                Hủy
              </button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? "Đang lưu…" : "Lưu"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {templateForm && (
        <Modal
          title={templateForm.id ? "Sửa mẫu điều phối" : "Thêm mẫu điều phối"}
          onClose={() => setTemplateForm(null)}
        >
          <form onSubmit={handleSaveTemplate}>
            {formError && <Notice error>{formError}</Notice>}
            <fieldset disabled={saving} className="form-fields">
              <div className="form-grid-2">
                <div className="form-group">
                  <label htmlFor="tpl-name">Tên mẫu *</label>
                  <input
                    id="tpl-name"
                    value={templateForm.name}
                    onChange={(e) =>
                      setTemplateForm({ ...templateForm, name: e.target.value })
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="tpl-desc">Mô tả ngắn</label>
                  <input
                    id="tpl-desc"
                    value={templateForm.description}
                    onChange={(e) =>
                      setTemplateForm({ ...templateForm, description: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="tpl-prompt">Nội dung Prompt *</label>
                <textarea
                  id="tpl-prompt"
                  rows={7}
                  value={templateForm.prompt_text}
                  onChange={(e) =>
                    setTemplateForm({ ...templateForm, prompt_text: e.target.value })
                  }
                  required
                />
              </div>

              <div className="form-group">
                <label>Quyền mặc định của mẫu</label>
                <div className="perm-row">
                  <label className="perm-check">
                    <input
                      type="checkbox"
                      checked={templateForm.allow_reply}
                      onChange={(e) =>
                        setTemplateForm({ ...templateForm, allow_reply: e.target.checked })
                      }
                    />
                    Tự trả lời (Reply)
                  </label>
                  <label className="perm-check">
                    <input
                      type="checkbox"
                      checked={templateForm.allow_retry}
                      onChange={(e) =>
                        setTemplateForm({ ...templateForm, allow_retry: e.target.checked })
                      }
                    />
                    Thử lại (Retry)
                  </label>
                  <label className="perm-check">
                    <input
                      type="checkbox"
                      checked={templateForm.allow_need_human}
                      onChange={(e) =>
                        setTemplateForm({
                          ...templateForm,
                          allow_need_human: e.target.checked,
                        })
                      }
                    />
                    Hỏi người (Need Human)
                  </label>
                  <label className="perm-turns-input">
                    Tối đa
                    <input
                      type="number"
                      min={1}
                      max={50}
                      value={templateForm.max_turns}
                      onChange={(e) =>
                        setTemplateForm({
                          ...templateForm,
                          max_turns: Number(e.target.value) || 10,
                        })
                      }
                    />
                    lượt
                  </label>
                </div>
              </div>

              <label className="perm-check">
                <input
                  type="checkbox"
                  checked={templateForm.is_default}
                  onChange={(e) =>
                    setTemplateForm({ ...templateForm, is_default: e.target.checked })
                  }
                />
                Đặt làm mẫu mặc định khi tạo Agent mới
              </label>
            </fieldset>
            <div className="dialog-actions">
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setTemplateForm(null)}
                disabled={saving}
              >
                Hủy
              </button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? "Đang lưu…" : "Lưu"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {deleteAgentTarget && (
        <Confirm
          title={`Xóa Agent ${deleteAgentTarget.name}?`}
          onClose={() => setDeleteAgentTarget(null)}
          onConfirm={async () => {
            await request(resource("/v1/agents", deleteAgentTarget.id), "DELETE");
            agents.reload();
          }}
        >
          Xóa Agent cùng snapshot và các liên kết danh mục. Chỉ bị chặn nếu còn Process sử dụng.
        </Confirm>
      )}

      {deleteTemplateTarget && (
        <Confirm
          title={`Xóa mẫu "${deleteTemplateTarget.name}"?`}
          onClose={() => setDeleteTemplateTarget(null)}
          onConfirm={async () => {
            await request(
              resource("/v1/agent-templates", deleteTemplateTarget.id),
              "DELETE",
            );
            templates.reload();
          }}
        >
          Các Agent đang dùng sẽ giữ nguyên nội dung prompt đã lưu trước đó.
        </Confirm>
      )}
    </>
  );
}
