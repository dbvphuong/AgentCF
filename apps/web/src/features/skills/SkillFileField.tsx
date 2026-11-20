import type { Field } from "../../shared/ui";
import type { RecordData } from "../../shared/api";
import { PcPathInput } from "../../shared/PcPathInput";

export function skillSourceFields(runners: RecordData[]): Field[] {
  return [
    { key: "source_runner_id", label: "PC chứa file Skill", type: "select", options: runners.filter(r => r.status !== "disabled") },
    { key: "source_path", label: "File .md chính của Skill", render: (id, value, onChange, values) =>
      <PcPathInput id={id} value={String(value ?? "")} runnerId={values.source_runner_id} onChange={onChange}
        canBrowse={runners.some(r => r.id === values.source_runner_id && ["online", "busy"].includes(r.display_status ?? r.status))} /> },
  ];
}

export function sourcePayload(data: RecordData): RecordData {
  const source_path = data.source_path?.trim() || null;
  const source_runner_id = data.source_runner_id || null;
  if (source_path && !source_runner_id) throw Error("Chọn PC chứa file Skill.");
  if (source_runner_id && !source_path) throw Error("Nhập đường dẫn hoặc chọn file .md chính của Skill.");
  return { ...data, source_path, source_runner_id };
}
