import { useState } from "react";
import type { ReactNode } from "react";
import { request, resource } from "./api";
import type { RecordData } from "./api";
import { Confirm, EntityForm, Modal, Notice, useResource } from "./ui";
import type { Field } from "./ui";
import { TechnicalDetails } from "./TechnicalDetails";

export function Catalog({
  title,
  path,
  fields,
  columns,
  extra,
  extraFormActions,
  onChanged,
  initialValues,
  preparePayload,
  toolbar,
  extraToolbar,
  filterRow,
  onValuesChange,
  deleteDescription,
}: {
  title: string;
  path: string;
  fields: Field[];
  columns: { label: string; render: (row: RecordData) => ReactNode }[];
  extra?: (row: RecordData, reload: () => void) => ReactNode;
  extraFormActions?: (
    values: RecordData,
    isSaving: boolean,
    editing: RecordData | null,
  ) => ReactNode;
  onChanged?: () => void;
  initialValues?: (row: RecordData) => RecordData;
  preparePayload?: (payload: RecordData) => RecordData;
  toolbar?: ReactNode;
  extraToolbar?: (reload: () => void) => ReactNode;
  filterRow?: (row: RecordData) => boolean;
  onValuesChange?: (values: RecordData, previous: RecordData) => RecordData;
  deleteDescription?: ReactNode;
}) {
  const { data, error, loading, reload } = useResource<RecordData[]>(path);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<RecordData | null>(null);
  const [action, setAction] = useState<{
    row: RecordData;
  } | null>(null);
  const changed = () => {
    reload();
    onChanged?.();
  };
  const rows = (data ?? []).filter(
    (row) =>
      row.status !== "archived" &&
      (!filterRow || filterRow(row)) &&
      `${row.name} ${row.id}`.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <section className="panel">
      <div className="toolbar catalog-toolbar">
        {toolbar}
        <input
          aria-label={`Tìm ${title}`}
          placeholder="Tìm theo tên hoặc ID…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button className="btn btn-outline" onClick={reload}>
          Làm mới
        </button>
        {extraToolbar?.(reload)}
        <button
          className="btn btn-primary"
          style={{ marginLeft: "auto" }}
          onClick={() => setEditing({})}
        >
          + Thêm mới
        </button>
      </div>
      {error && <Notice error>{error}</Notice>}
      {loading ? (
        <Notice>Đang tải…</Notice>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Tên</th>
                {columns.map((c) => (
                  <th key={c.label}>{c.label}</th>
                ))}
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    <strong>{row.name}</strong>
                    <TechnicalDetails values={{ ID: row.id }} />
                  </td>
                  {columns.map((c) => (
                    <td key={c.label}>{c.render(row)}</td>
                  ))}
                  <td>
                    <div className="row-actions">
                        <button
                          className="btn btn-outline btn-sm"
                          onClick={async () => {
                            if (row.id) {
                              try {
                                const detail = await request<RecordData>(
                                  resource(path, row.id),
                                );
                                if (
                                  detail &&
                                  typeof detail === "object" &&
                                  !Array.isArray(detail)
                                ) {
                                  setEditing(detail);
                                  return;
                                }
                              } catch {
                                // fallback to row
                              }
                            }
                            setEditing(row);
                          }}
                        >
                          Sửa
                        </button>
                      {extra?.(row, changed)}
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => setAction({ row })}
                      >
                        Xóa
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!rows.length && (
                <tr>
                  <td colSpan={columns.length + 2} className="empty-state">
                    Chưa có dữ liệu phù hợp.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      {editing && (
        <Modal
          title={`${editing.id ? "Sửa" : "Thêm"} ${title}`}
          onClose={() => setEditing(null)}
        >
          <EntityForm
            fields={fields}
            initial={initialValues ? initialValues(editing) : editing}
            onValuesChange={onValuesChange}
            extraActions={
              extraFormActions
                ? (vals, isSaving) => extraFormActions(vals, isSaving, editing)
                : undefined
            }
            onCancel={() => setEditing(null)}
            onSave={async (payload) => {
              await request(
                editing.id ? resource(path, editing.id) : path,
                editing.id ? "PATCH" : "POST",
                editing.id ? (preparePayload ? preparePayload(payload) : payload)
                  : { id: crypto.randomUUID(), ...(preparePayload ? preparePayload(payload) : payload) },
              );
              setEditing(null);
              changed();
            }}
          />
        </Modal>
      )}
      {action && (
        <Confirm
          title={`Xóa ${action.row.name}?`}
          onClose={() => setAction(null)}
          onConfirm={async () => {
            await request(
              resource(path, action.row.id),
              "DELETE",
            );
            changed();
          }}
        >
          {deleteDescription ?? "Server sẽ từ chối xóa nếu dữ liệu đang được sử dụng. Các phiên bản và lịch sử đã phát sinh vẫn được bảo vệ."}
        </Confirm>
      )}
    </section>
  );
}
