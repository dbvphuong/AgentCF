import { EntityForm } from "../../../shared/ui";
import type { RecordData } from "../../../shared/api";
import { EFFORT_OPTION_LABELS, shouldShowReasoningEffort } from "./modelLevel";

export function NodeForm({ node, kind, agents, models, skills, runners, robotVersions, onCancel, onSave }: {
  node: RecordData; kind: string; agents: RecordData[]; models: RecordData[]; skills: RecordData[];
  runners: RecordData[]; robotVersions: RecordData[]; onCancel: () => void;
  onSave: (data: RecordData) => Promise<void>;
}) {
  const availableModels = (adapter: string) => models.filter(m => m.tool_id === adapter && m.status === "active");
  const findModel = (adapter: string, id?: string) => availableModels(adapter).find(m => m.id === id);
  const adapter = node.runtime?.adapter ?? "codex";
  const modelId = node.runtime?.tool_model_id ?? availableModels(adapter).find(m => m.model_identifier === node.runtime?.model_id)?.id;
  const initialModel = findModel(adapter, modelId);
  const initialEffort = shouldShowReasoningEffort(adapter, initialModel)
    ? (node.runtime?.reasoning_effort ?? "default")
    : "default";
  return <EntityForm initial={{ ...node, adapter, node_model_id: modelId ?? "", node_reasoning_effort: initialEffort }}
    onValuesChange={(next, previous) => {
      if (kind !== "agent") return next;
      if (next.adapter !== previous.adapter) {
        next.node_model_id = "";
        next.node_reasoning_effort = "default";
      }
      if (next.node_model_id !== previous.node_model_id) next.node_reasoning_effort = "default";
      if (next.skill_id !== previous.skill_id) {
        const skill = skills.find(s => s.id === next.skill_id);
        if (skill?.source_runner_id) next.runner_id = skill.source_runner_id;
      }
      return next;
    }} fields={[
      { key: "name", label: "Tên bước", required: true },
      { key: "agent_id", label: "Agent điều phối", type: "select", required: true, options: agents,
        hint: "Agent dùng model API để giao việc và kiểm tra tiến độ, lỗi, chất lượng kết quả của công cụ AI." },
      ...(kind === "agent" ? [
        { key: "skill_id", label: "Skill", type: "select" as const, required: true, options: skills,
          hint: "Skill thuộc Project hoặc Global; dùng cấu hình đã lưu." },
        { key: "adapter", label: "Công cụ AI thực thi", type: "select" as const, required: true, default: "codex", options: [
          { id: "codex", name: "Codex CLI" }, { id: "antigravity", name: "Antigravity" },
        ] },
        { key: "node_model_id", label: "Model thực thi", type: "select" as const, required: true,
          getOptions: (values: RecordData) => availableModels(values.adapter).map(m => ({ ...m,
            name: `${m.name} · ${m.model_identifier}` })),
          hint: "Chỉ hiện model đã bật của công cụ đã chọn (nhiều model Antigravity đã gắn sẵn mức suy luận). Thêm/sửa tại Settings → Công cụ AI trên PC." },
        { key: "node_reasoning_effort", label: "Mức suy luận (Level)", type: "select" as const,
          hidden: (values: RecordData) => !shouldShowReasoningEffort(values.adapter, findModel(values.adapter, values.node_model_id)),
          getOptions: (values: RecordData) => [
            { id: "default", name: "Mặc định của CLI" },
            ...["low", "medium", "high", ...(values.adapter === "codex" ? ["xhigh", "max"] : [])]
              .map(id => ({ id, name: EFFORT_OPTION_LABELS[id] ?? id })),
          ], hint: "Áp dụng riêng cho bước này khi model chưa gắn sẵn mức suy luận. Mức cao hơn thường cần nhiều thời gian hơn." },
        { key: "instructions", label: "Nhiệm vụ bổ sung (không bắt buộc)", type: "textarea" as const,
          hint: "Mặc định chạy Skill đã chọn cho chủ đề của lần chạy. Chỉ nhập yêu cầu riêng cho bước này; không cần chép lại Skill hoặc nhập lại chủ đề." },
        { key: "runner_id", label: "PC thực thi", type: "select" as const, options: runners,
          hint: "Tự chọn PC chứa file Skill. Server kiểm tra khi lưu và chạy Process." },
      ] : [
        { key: "robot_version_id", label: "Robot version", type: "select" as const, required: true, options: robotVersions },
        { key: "runner_id", label: "PC thực thi", type: "select" as const, required: true, options: runners },
      ]),
      { key: "execution_timeout_seconds", label: "Timeout (giây)", type: "number", min: 1, max: 86400, default: 300, required: true, advanced: true },
    ]} onCancel={onCancel} onSave={onSave} />;
}
