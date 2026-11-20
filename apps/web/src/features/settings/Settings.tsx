import { useState } from "react";
import { Catalog } from "../../shared/Catalog";
import {
  EntityForm,
  Modal,
  Notice,
  PageHead,
  Tabs,
  useResource,
} from "../../shared/ui";
import { request, resource } from "../../shared/api";
import type { RecordData } from "../../shared/api";
import { AiTools } from "./AiTools";

function ProviderFormExtraActions({
  values,
  isSaving,
  editingRow,
}: {
  values: RecordData;
  isSaving: boolean;
  editingRow: RecordData | null;
}) {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<{
    ok: boolean;
    status?: number;
    error?: string;
  } | null>(null);

  const runTest = async () => {
    if (!values.base_url) {
      setResult({
        ok: false,
        error: "Vui lòng nhập Base URL trước khi kiểm tra",
      });
      return;
    }
    setTesting(true);
    setResult(null);
    try {
      const res = await request<RecordData>(
        "/v1/settings/providers-test",
        "POST",
        {
          base_url: values.base_url,
          api_format: values.api_format || "custom",
          api_key: values.api_key || undefined,
          request_timeout_seconds: values.request_timeout_seconds
            ? Number(values.request_timeout_seconds)
            : 30,
          provider_id: editingRow?.id || undefined,
        },
      );
      setResult({
        ok: !!res.ok,
        status: res.http_status,
        error: res.error,
      });
    } catch (e) {
      setResult({ ok: false, error: (e as Error).message });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="provider-modal-test">
      <button
        type="button"
        className="btn btn-outline"
        disabled={testing || isSaving}
        onClick={runTest}
      >
        {testing ? "Đang kiểm tra…" : "Test API"}
      </button>
      {result && (
        <span
          className={`api-test-badge ${result.ok ? "badge-success" : "badge-error"}`}
          role="status"
        >
          {result.ok
            ? `✓ HTTP ${result.status ?? 200} OK — Kết nối thành công`
            : `✗ ${result.status ? `HTTP ${result.status}` : ""}${result.status && result.error ? " · " : ""}${result.error || "Kết nối thất bại"}`}
        </span>
      )}
    </div>
  );
}

function ModelFormExtraActions({
  values,
  isSaving,
}: {
  values: RecordData;
  isSaving: boolean;
}) {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<{
    ok: boolean;
    status?: number;
    error?: string;
  } | null>(null);

  const runTest = async () => {
    if (!values.provider_id || !values.model_identifier) {
      setResult({
        ok: false,
        error: "Vui lòng chọn Provider và nhập Model ID",
      });
      return;
    }
    setTesting(true);
    setResult(null);
    try {
      const res = await request<RecordData>(
        "/v1/settings/providers-test",
        "POST",
        {
          provider_id: values.provider_id,
          model: values.model_identifier,
        },
      );
      setResult({
        ok: !!res.ok,
        status: res.http_status,
        error: res.error,
      });
    } catch (e) {
      setResult({ ok: false, error: (e as Error).message });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="provider-modal-test">
      <button
        type="button"
        className="btn btn-outline"
        disabled={testing || isSaving}
        onClick={runTest}
      >
        {testing ? "Đang kiểm tra…" : "Test Model"}
      </button>
      {result && (
        <span
          className={`api-test-badge ${result.ok ? "badge-success" : "badge-error"}`}
          role="status"
        >
          {result.ok
            ? `✓ HTTP ${result.status ?? 200} OK — Phản hồi thành công`
            : `✗ ${result.status ? `HTTP ${result.status}` : ""}${result.status && result.error ? " · " : ""}${result.error || "Kết nối thất bại"}`}
        </span>
      )}
    </div>
  );
}

export function Settings() {
  const [tab, setTab] = useState("Providers & Models API");
  const [apiTab, setApiTab] = useState("Providers API");
  const providers = useResource<RecordData[]>(
    "/v1/settings/providers?status=active",
  );
  const general = useResource<RecordData>("/v1/settings/general");
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState("");
  const [testResult, setTestResult] = useState("");
  return (
    <>
      <PageHead title="Settings" />
      <Tabs
        items={["Providers & Models API", "Công cụ AI trên PC", "Roles", "General"]}
        value={tab}
        onChange={setTab}
      />
      {tab === "Providers & Models API" && <>
        <p>Provider và model API dùng cho Agent điều phối giao việc và kiểm tra kết quả. Model của Codex/Antigravity được cấu hình riêng trong Công cụ AI trên PC.</p>
        <Tabs items={["Providers API", "Models API"]} value={apiTab} onChange={setApiTab} />
      </>}
      {tab === "Công cụ AI trên PC" && <AiTools />}
      {tab === "Providers & Models API" && apiTab === "Providers API" && (
        <Catalog
          title="Providers API"
          path="/v1/settings/providers"
          onChanged={providers.reload}
          columns={[
            { label: "API format", render: (r) => r.api_format },
            { label: "Base URL", render: (r) => r.base_url },
            {
              label: "API key",
              render: (r) =>
                r.api_key_masked ? "Đã cấu hình" : "Chưa cấu hình",
            },
            { label: "Trạng thái", render: (r) => r.status },
          ]}
          extraFormActions={(values, isSaving, editingRow) => (
            <ProviderFormExtraActions
              values={values}
              isSaving={isSaving}
              editingRow={editingRow}
            />
          )}
          extra={(row) => (
            <button
              className="btn btn-outline btn-sm"
              disabled={!!testing}
              onClick={async () => {
                setTesting(row.id);
                try {
                  const result = await request(
                    `${resource("/v1/settings/providers", row.id)}/test`,
                    "POST",
                  );
                  setTestResult(
                    `${row.name}: ${result.ok ? "Kết nối thành công" : "Kết nối thất bại"}${result.http_status ? ` (HTTP ${result.http_status})` : ` · ${result.error}`}`,
                  );
                } catch (e) {
                  setTestResult((e as Error).message);
                } finally {
                  setTesting("");
                }
              }}
            >
              {testing === row.id ? "Đang kiểm tra…" : "Test API"}
            </button>
          )}
          fields={[
            { key: "name", label: "Tên", required: true },
            {
              key: "api_format",
              label: "API format",
              type: "select",
              required: true,
              options: ["openai", "anthropic", "google", "custom"].map(
                (id) => ({ id, name: id }),
              ),
            },
            { key: "base_url", label: "Base URL", required: true },
            {
              key: "api_key",
              label: "API key",
              type: "password",
              hint: "Bấm biểu tượng mắt để xem hoặc sửa khóa API. Khóa được mã hóa khi lưu trữ.",
            },
            {
              key: "request_timeout_seconds",
              label: "Request timeout (giây)",
              type: "number",
              min: 1,
              max: 300,
              default: 60,
              required: true,
            },
            {
              key: "status",
              label: "Trạng thái",
              type: "select",
              default: "active",
              options: ["active", "disabled"].map((id) => ({ id, name: id })),
            },
          ]}
        />
      )}
      {tab === "Providers & Models API" && apiTab === "Models API" && (
        <>
          {providers.error && <Notice error>{providers.error}</Notice>}
          <Catalog
            title="Models API"
            path="/v1/settings/models"
            columns={[
              { label: "Model ID", render: (r) => r.model_identifier },
              {
                label: "Provider",
                render: (r) =>
                  providers.data?.find((p) => p.id === r.provider_id)?.name ??
                    "Không có tên Provider",
              },
              { label: "Trạng thái", render: (r) => r.status },
            ]}
            extraFormActions={(values, isSaving) => (
              <ModelFormExtraActions values={values} isSaving={isSaving} />
            )}
            extra={(row) => (
              <button
                className="btn btn-outline btn-sm"
                disabled={!!testing}
                onClick={async () => {
                  setTesting(row.id);
                  try {
                    const result = await request<RecordData>(
                      "/v1/settings/providers-test",
                      "POST",
                      {
                        provider_id: row.provider_id,
                        model: row.model_identifier,
                      },
                    );
                    setTestResult(
                      `${row.name} (${row.model_identifier}): ${result.ok ? "Kết nối & Model thành công" : "Kết nối thất bại"}${result.http_status ? ` (HTTP ${result.http_status})` : ` · ${result.error}`}`,
                    );
                  } catch (e) {
                    setTestResult((e as Error).message);
                  } finally {
                    setTesting("");
                  }
                }}
              >
                {testing === row.id ? "Đang kiểm tra…" : "Test Model"}
              </button>
            )}
            fields={[
              { key: "name", label: "Tên", required: true },
              {
                key: "provider_id",
                label: "Provider",
                type: "select",
                immutable: true,
                required: true,
                options: providers.data ?? [],
              },
              { key: "model_identifier", label: "Model ID", required: true },
              {
                key: "max_output_tokens",
                label: "Max output tokens",
                type: "number",
                min: 1,
              },
              {
                key: "temperature",
                label: "Temperature",
                type: "number",
                default: 0.7,
                min: 0,
                max: 2,
                step: 0.1,
              },
              {
                key: "status",
                label: "Trạng thái",
                type: "select",
                default: "active",
                options: ["active", "disabled"].map((id) => ({ id, name: id })),
              },
            ]}
          />
        </>
      )}
      {tab === "Roles" && (
        <Catalog
          title="Roles"
          path="/v1/settings/roles"
          columns={[{ label: "Duties", render: (r) => r.description }]}
          fields={[
            { key: "name", label: "Tên", required: true },
            { key: "description", label: "Duties", type: "textarea" },
          ]}
        />
      )}
      {tab === "General" && (
        <section className="panel">
          {general.error && <Notice error>{general.error}</Notice>}
          {saved && <Notice>Đã lưu cấu hình.</Notice>}
          {general.data && (
            <EntityForm
              key={JSON.stringify(general.data)}
              initial={general.data}
              fields={[
                {
                  key: "default_task_timeout_seconds",
                  label: "Task timeout (giây)",
                  type: "number",
                  required: true,
                  min: 10,
                  max: 86400,
                },
                {
                  key: "default_logs_lines",
                  label: "Số dòng Logs mặc định",
                  type: "number",
                  required: true,
                  min: 10,
                  max: 10000,
                },
              ]}
              onCancel={general.reload}
              onSave={async (data) => {
                await request("/v1/settings/general", "PUT", data);
                setSaved(true);
                general.reload();
              }}
            />
          )}
        </section>
      )}
      {testResult && (
        <Modal title="Kết quả Test API" onClose={() => setTestResult("")}>
          <p>{testResult}</p>
          <p className="muted">
            Kiểm tra endpoint của provider; không xác nhận khả năng chạy từng
            model.
          </p>
        </Modal>
      )}
    </>
  );
}
