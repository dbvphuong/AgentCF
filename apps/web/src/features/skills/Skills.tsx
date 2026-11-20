import { useState } from "react";
import { Catalog } from "../../shared/Catalog";
import {
  Notice,
  PageHead,
  Tabs,
  useResource,
} from "../../shared/ui";
import type { RecordData } from "../../shared/api";
import { GLOBAL, scopeField, scopePayload } from "./projectScope";
import { skillSourceFields, sourcePayload } from "./SkillFileField";

export function Skills() {
  const [tab, setTab] = useState("Skills");
  const agents = useResource<RecordData[]>("/v1/agents");
  const projects = useResource<RecordData[]>("/v1/projects");
  const runners = useResource<RecordData[]>("/v1/runners");
  const [projectFilter, setProjectFilter] = useState("");
  return (
    <>
      <PageHead title="Skills" />
      <Tabs items={["Skills", "Tools"]} value={tab} onChange={setTab} />
      {projects.error && <Notice error>{projects.error}</Notice>}
      {runners.error && <Notice error>{runners.error}</Notice>}
      {tab === "Skills" ? (
        <Catalog
          title="Skills"
          path="/v1/skills"
            deleteDescription="Xóa Skill và liên kết Agent/Project nếu không còn Process sử dụng. Không xóa file Skill hoặc output trên PC."
          columns={[
            { label: "Mô tả", render: (r) => r.description },
            { label: "Project", render: (r) => r.is_global ? <span className="badge">Global</span> : r.projects?.map((p: RecordData) => p.name).join(", ") },
          ]}
          toolbar={<select aria-label="Lọc Skill theo Project" value={projectFilter} onChange={e => setProjectFilter(e.target.value)}>
            <option value="">Tất cả Project</option><option value={GLOBAL}>Chỉ Global</option>
            {projects.data?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>}
          filterRow={row => !projectFilter || (projectFilter === GLOBAL ? row.is_global : row.is_global || row.project_ids?.includes(projectFilter))}
          initialValues={row => ({ ...row, scope_selection: row.id ? (row.is_global ? [GLOBAL] : row.project_ids) : [] })}
          preparePayload={data => sourcePayload(scopePayload(data))}
          fields={[
            { key: "name", label: "Tên", required: true },
            { key: "description", label: "Mô tả", type: "textarea" },
            ...skillSourceFields(runners.data ?? []),
            scopeField(projects.data ?? []),
          ]}
        />
      ) : (
        <Catalog
          title="Tools"
          path="/v1/skills/tools"
          columns={[
            { label: "Mô tả", render: (r) => r.description },
            { label: "Loại", render: (r) => r.tool_type },
            {
              label: "Agent điều phối được phép",
              render: (r) =>
                agents.error
                  ? "Không tải được Agent"
                  : agents.data
                      ?.filter((a) => a.allowed_tool_ids?.includes(r.id))
                      .map((a) => a.name)
                      .join(", ") || "—",
            },
          ]}
          fields={[
            { key: "name", label: "Tên", required: true },
            { key: "description", label: "Mô tả", type: "textarea" },
            {
              key: "tool_type",
              label: "Loại",
              type: "select",
              default: "internal",
              options: ["cli", "api", "internal"].map((id) => ({
                id,
                name: id,
              })),
            },
            { key: "configuration", label: "Cấu hình JSON", type: "json" },
          ]}
        />
      )}
    </>
  );
}
