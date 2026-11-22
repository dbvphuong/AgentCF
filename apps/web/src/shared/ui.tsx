import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import { request } from "./api";
import type { RecordData } from "./api";
import { CloseIcon } from "./icons";

export function useResource<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const previousPath = useRef(path);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    if (previousPath.current !== path) setData(null);
    previousPath.current = path;
    request<T>(path, "GET", undefined, controller.signal)
      .then(setData)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [path, revision]);
  return {
    data,
    error,
    loading,
    replace: setData,
    reload: () => setRevision((n) => n + 1),
  };
}

export function Notice({
  children,
  error = false,
}: {
  children: ReactNode;
  error?: boolean;
}) {
  return (
    <div
      className={error ? "error-alert" : "notice"}
      role={error ? "alert" : "status"}
    >
      {children}
    </div>
  );
}
export function PageHead({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <h1>{title}</h1>
      <div className="row-actions">{children}</div>
    </div>
  );
}
export function Tabs({
  items,
  value,
  onChange,
}: {
  items: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="review-tabs" aria-label="Các mục">
      {items.map((item) => (
        <button
          type="button"
          key={item}
          aria-pressed={value === item}
          className={value === item ? "active" : ""}
          onClick={() => onChange(item)}
        >
          {item}
        </button>
      ))}
    </div>
  );
}
export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    ref.current?.showModal();
    document.dispatchEvent(new Event("agentcf:modalchange"));
    return () => { document.dispatchEvent(new Event("agentcf:modalchange")); };
  }, []);
  return (
    <dialog
      ref={ref}
      aria-labelledby={id}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      <div className="dialog-head">
        <h2 id={id}>{title}</h2>
        <button
          type="button"
          className="icon-button"
          aria-label="Đóng"
          onClick={onClose}
        >
          <CloseIcon size={16} />
        </button>
      </div>
      {children}
    </dialog>
  );
}

export interface Field {
  key: string;
  label: string;
  type?:
    | "text"
    | "textarea"
    | "number"
    | "password"
    | "select"
    | "multi"
    | "checklist"
    | "json"
    | "date";
  required?: boolean;
  options?: RecordData[];
  default?: unknown;
  min?: number;
  max?: number;
  step?: number;
  hint?: string;
  immutable?: boolean;
  exclusiveValue?: string;
  advanced?: boolean;
  hidden?: (values: RecordData) => boolean;
  getOptions?: (values: RecordData) => RecordData[];
  render?: (id: string, value: unknown, onChange: (value: string) => void, values: RecordData) => ReactNode;
}
export function EntityForm({
  fields,
  initial = {},
  onSave,
  onCancel,
  extraActions,
  submitLabel = "Lưu",
  busyLabel = "Đang lưu…",
  onValuesChange,
}: {
  fields: Field[];
  initial?: RecordData;
  onSave: (data: RecordData) => Promise<unknown>;
  onCancel: () => void;
  extraActions?: (values: RecordData, isSaving: boolean) => ReactNode;
  submitLabel?: string;
  busyLabel?: string;
  onValuesChange?: (values: RecordData, previous: RecordData) => RecordData;
}) {
  const [values, setRawValues] = useState<RecordData>(() =>
    Object.fromEntries(
      fields.map((f) => [
        f.key,
        f.type === "password"
          ? (initial[f.key] ?? "")
          : f.type === "json"
            ? JSON.stringify(initial[f.key] ?? f.default ?? {}, null, 2)
            : (initial[f.key] ?? f.default ?? (["multi", "checklist"].includes(f.type ?? "") ? [] : "")),
      ]),
    ),
  );
  const setValues = (next: RecordData) => setRawValues(previous => onValuesChange ? onValuesChange(next, previous) : next);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState<Record<string, boolean>>({});
  const formId = useId();
  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        setError("");
        setBusy(true);
        try {
          const payload: RecordData = {};
          for (const field of fields) {
            if (field.hidden?.(values)) continue;
            const value = values[field.key];
            if (field.type === "password" && !value) continue;
            payload[field.key] =
              field.type === "number"
                ? value === ""
                  ? null
                  : Number(value)
                : field.type === "json"
                  ? JSON.parse(value)
                  : typeof value === "string"
                    ? value.trim()
                    : value;
            if (
              field.required &&
              (payload[field.key] === "" || payload[field.key] == null || (Array.isArray(payload[field.key]) && !payload[field.key].length))
            )
              throw new Error(`Vui lòng nhập ${field.label}.`);
          }
          await onSave(payload);
        } catch (e) {
          setError(e instanceof Error ? e.message : "Không lưu được dữ liệu.");
        } finally {
          setBusy(false);
        }
      }}
    >
      {error && <Notice error>{error}</Notice>}
      <fieldset disabled={busy} className="form-fields">
        {(() => {
          const renderField = (field: Field) => {
          const id = `${formId}-${field.key}`;
          return (
            <div className="form-group" key={field.key}>
              <label htmlFor={id}>
                {field.label}
                {field.required && " *"}
                {field.hint && (
                  <span
                    className="help"
                    tabIndex={0}
                    title={field.hint}
                    aria-label={field.hint}
                  >
                    ?
                  </span>
                )}
              </label>
                {field.render ? field.render(id, values[field.key], value => setValues({ ...values, [field.key]: value }), values) : field.type === "checklist" ? (
                  <div id={id} role="group" aria-label={field.label}>
                    {field.options?.map(option => (
                      <label key={option.id} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <input type="checkbox" checked={values[field.key].includes(option.id)}
                          onChange={event => {
                            const chosen: string[] = values[field.key];
                            const next = !event.target.checked ? chosen.filter(v => v !== option.id)
                              : option.id === field.exclusiveValue ? [option.id]
                              : [...chosen.filter(v => v !== field.exclusiveValue), option.id];
                            setValues({ ...values, [field.key]: next });
                          }} />{option.name}
                      </label>
                    ))}
                  </div>
                ) : field.type === "select" || field.type === "multi" ? (
                <select
                  id={id}
                  disabled={field.immutable && !!initial.id}
                  required={field.required}
                  multiple={field.type === "multi"}
                  value={values[field.key]}
                  onChange={(e) =>
                    setValues({
                      ...values,
                      [field.key]:
                        field.type === "multi"
                          ? Array.from(e.target.selectedOptions, (o) => o.value)
                          : e.target.value,
                    })
                  }
                >
                  {field.type !== "multi" && <option value="">Chọn…</option>}
                  {(field.getOptions ? field.getOptions(values) : field.options)?.map((o) => (
                    <option value={o.id} key={o.id}>
                      {o.name}
                    </option>
                  ))}
                </select>
              ) : field.type === "textarea" || field.type === "json" ? (
                <textarea
                  id={id}
                  rows={field.type === "json" ? 6 : 4}
                  required={field.required}
                  value={values[field.key]}
                  onChange={(e) =>
                    setValues({ ...values, [field.key]: e.target.value })
                  }
                  spellCheck={field.type !== "json"}
                />
              ) : field.type === "password" ? (
                <div className="password-input-group">
                  <input
                    id={id}
                    type={showPassword[field.key] ? "text" : "password"}
                    autoComplete="new-password"
                    required={field.required}
                    value={values[field.key]}
                    onChange={(e) =>
                      setValues({ ...values, [field.key]: e.target.value })
                    }
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() =>
                      setShowPassword((prev) => ({
                        ...prev,
                        [field.key]: !prev[field.key],
                      }))
                    }
                    title={showPassword[field.key] ? "Ẩn khóa" : "Hiện khóa"}
                    aria-label={
                      showPassword[field.key] ? "Ẩn khóa" : "Hiện khóa"
                    }
                  >
                    {showPassword[field.key] ? (
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg>
                    ) : (
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                </div>
              ) : (
                <input
                  id={id}
                  type={field.type ?? "text"}
                  autoComplete="off"
                  required={field.required}
                  min={field.min}
                  max={field.max}
                  step={field.step}
                  value={values[field.key]}
                  onChange={(e) =>
                    setValues({ ...values, [field.key]: e.target.value })
                  }
                />
              )}
            </div>
          );
          };
          const visibleFields = fields.filter(field => !field.hidden?.(values));
          return <>
            {visibleFields.filter(field => !field.advanced).map(renderField)}
            {visibleFields.some(field => field.advanced) && <details className="advanced-settings">
              <summary>Cấu hình nâng cao</summary>
              <div className="form-fields">{visibleFields.filter(field => field.advanced).map(renderField)}</div>
            </details>}
          </>;
        })()}
      </fieldset>
      <div className="form-actions">
        {extraActions && (
          <div className="form-extra-actions">{extraActions(values, busy)}</div>
        )}
        <div className="form-primary-actions">
          <button
            type="button"
            className="btn btn-outline"
            disabled={busy}
            onClick={onCancel}
          >
            Hủy
          </button>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? busyLabel : submitLabel}
          </button>
        </div>
      </div>
    </form>
  );
}

export function Confirm({
  title,
  children,
  onConfirm,
  onClose,
  confirmLabel = "Xác nhận",
  danger = true,
  onError,
}: {
  title: string;
  children: ReactNode;
  onConfirm: () => Promise<unknown>;
  onClose: () => void;
  confirmLabel?: string;
  danger?: boolean;
  onError?: (error: Error) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <Modal
      title={title}
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <p>{children}</p>
      {error && <Notice error>{error}</Notice>}
      <div className="form-actions">
        <button
          disabled={busy}
          type="button"
          className="btn btn-outline"
          onClick={onClose}
        >
          Quay lại
        </button>
        <button
          disabled={busy}
          className={danger ? "btn btn-danger" : "btn btn-primary"}
          onClick={async () => {
            setBusy(true);
            try {
              await onConfirm();
              onClose();
            } catch (e) {
              const failure = e instanceof Error ? e : new Error(String(e));
              setError(failure.message);
              onError?.(failure);
            } finally {
              setBusy(false);
            }
          }}
        >
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
