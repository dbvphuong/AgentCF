import { Catalog } from "../../shared/Catalog";
import { Notice, PageHead, useResource } from "../../shared/ui";
import type { RecordData } from "../../shared/api";

export function Agents() {
  const roles = useResource<RecordData[]>("/v1/settings/roles?status=active");
  const models = useResource<RecordData[]>("/v1/settings/models?status=active");
  const skills = useResource<RecordData[]>("/v1/skills?status=active");
  const tools = useResource<RecordData[]>("/v1/skills/tools?status=active");
  const usage = useResource<RecordData>("/v1/overview/summary");
  return (
    <>
      <PageHead title="Agent điều phối" />
      <p>Agent dùng model API để thay bạn giao việc cho Codex/Antigravity và kiểm tra tiến độ, lỗi, chất lượng kết quả. Công cụ AI thực thi trực tiếp làm việc và giữ output trên PC.</p>
      {[roles, models, skills, tools, usage]
        .filter((r) => r.error)
        .map((r, i) => (
          <Notice key={i} error>
            {r.error}
          </Notice>
        ))}
      <Catalog
          deleteDescription="Xóa Agent cùng snapshot và các liên kết danh mục. Chỉ bị chặn nếu còn Process sử dụng. Nếu đang làm PM hoặc nằm trong Team nhưng chưa dùng ở node, sẽ gỡ các liên kết đó; bạn cần chọn PM mới cho Project liên quan. Không xóa Skill hoặc file trên PC."
        title="Agent điều phối"
        path="/v1/agents"
        columns={[
          { label: "Role", render: (r) => r.role_name },
          { label: "Model API", render: (r) => r.model_name },
          {
            label: "Skills",
            render: (r) =>
              r.skill_ids
                ?.map(
                  (id: string) =>
                    skills.data?.find((s) => s.id === id)?.name ?? "Skill không còn trong danh mục",
                )
                .join(", ") || "—",
          },
          {
            label: "Tokens tháng",
            render: (r) => {
              const item = usage.data?.agents_token_usage?.find(
                (a: RecordData) => a.agent_id === r.id,
              );
              return item?.total_tokens == null
                ? "— (Chưa có dữ liệu)"
                : Number(item.total_tokens).toLocaleString("vi-VN");
            },
          },
        ]}
        fields={[
          { key: "name", label: "Tên", required: true },
          {
            key: "role_id",
            label: "Role",
            type: "select",
            required: true,
            options: roles.data ?? [],
          },
          {
            key: "model_id",
            label: "Model API",
            type: "select",
            required: true,
            options: models.data ?? [],
          },
          { key: "instructions", label: "Hướng dẫn điều phối và kiểm tra", type: "textarea" },
          {
            key: "allowed_tool_ids",
            label: "Allowed tools",
            type: "multi",
            options: tools.data ?? [],
          },
        ]}
      />
    </>
  );
}
