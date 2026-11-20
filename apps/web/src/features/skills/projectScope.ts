import type { Field } from "../../shared/ui";
import type { RecordData } from "../../shared/api";

export const GLOBAL = "__global__";
export function scopeField(projects: RecordData[], defaultProject?: string): Field {
  return {
    key: "scope_selection", label: "Project", type: "checklist", required: true,
    exclusiveValue: GLOBAL, default: defaultProject ? [defaultProject] : [],
    options: [{ id: GLOBAL, name: "Global (tất cả Project)" }, ...projects],
    hint: "Tích một hoặc nhiều Project. Chọn Global để mọi Project sử dụng Skill này.",
  };
}
export function scopePayload(data: RecordData): RecordData {
  const { scope_selection, ...rest } = data;
  return { ...rest, is_global: scope_selection.includes(GLOBAL), project_ids: scope_selection.filter((id: string) => id !== GLOBAL) };
}
