import { EntityForm, Modal, Notice, useResource } from "../../shared/ui";
import { request } from "../../shared/api";
import type { RecordData } from "../../shared/api";
import { scopeField, scopePayload } from "./projectScope";
import { skillSourceFields, sourcePayload } from "./SkillFileField";

export function NewProjectSkill({ projectId, onClose, onCreated }: { projectId: string; onClose: () => void; onCreated: () => void }) {
  const projects = useResource<RecordData[]>("/v1/projects");
  const runners = useResource<RecordData[]>("/v1/runners");
  return <Modal title="Thêm Skill cho Project" onClose={onClose}>
    {runners.error && <Notice error>{runners.error}</Notice>}
    <EntityForm fields={[
      { key: "name", label: "Tên", required: true },
      { key: "description", label: "Mô tả", type: "textarea" },
      ...skillSourceFields(runners.data ?? []),
      scopeField(projects.data ?? [], projectId),
    ]} onCancel={onClose} onSave={async data => {
      await request("/v1/skills", "POST", { id: crypto.randomUUID(), ...sourcePayload(scopePayload(data)) });
      onCreated(); onClose();
    }} />
  </Modal>;
}
