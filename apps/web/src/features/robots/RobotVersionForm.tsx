import React, { useState } from "react";
import type { Robot, RobotVersion } from "./types";
import { createRobotVersion } from "./api";

interface RobotVersionFormProps {
  robot: Robot;
  onSuccess: (version: RobotVersion) => void;
  onCancel: () => void;
}

export const RobotVersionForm: React.FC<RobotVersionFormProps> = ({ robot, onSuccess, onCancel }) => {
  const [entrypoint, setEntrypoint] = useState("python main.py");
  const [contractVersion, setContractVersion] = useState("1.0.0");
  const [inputSchemaStr, setInputSchemaStr] = useState('{\n  "type": "object",\n  "properties": {}\n}');
  const [outputSchemaStr, setOutputSchemaStr] = useState('{\n  "type": "object",\n  "properties": {}\n}');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!entrypoint.trim()) {
      setError("Entrypoint không được để trống");
      return;
    }

    let inputSchema: Record<string, unknown> = {};
    let outputSchema: Record<string, unknown> = {};

    try {
      inputSchema = JSON.parse(inputSchemaStr);
    } catch {
      setError("Input Schema phải là chuỗi JSON hợp lệ");
      return;
    }

    try {
      outputSchema = JSON.parse(outputSchemaStr);
    } catch {
      setError("Output Schema phải là chuỗi JSON hợp lệ");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const created = await createRobotVersion(robot.id, {
        entrypoint: entrypoint.trim(),
        ready_to_use: true,
        contract_version: contractVersion.trim(),
        input_schema: inputSchema,
        output_schema: outputSchema,
      });
      onSuccess(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="run-form-card">
      <div className="form-header">
        <h3>Thêm phiên bản cho Robot: {robot.name}</h3>
        <p className="form-hint">
          Lưu xong có thể chọn phiên bản này trong Process. Mỗi phiên bản Robot giữ nguyên cấu hình để các lần chạy dùng đúng bản đã chọn.
        </p>
      </div>

      {error && <div className="error-box">{error}</div>}

      <form onSubmit={handleSubmit} className="standard-form">
        <div className="form-group">
          <label htmlFor="version-entrypoint" className="form-label">
            Entrypoint (Lệnh / File thực thi) <span className="required">*</span>
          </label>
          <input
            id="version-entrypoint"
            type="text"
            className="form-input"
            value={entrypoint}
            onChange={(e) => setEntrypoint(e.target.value)}
            placeholder="Ví dụ: python main.py hoặc cli_transcribe"
            disabled={loading}
            required
          />
          <span className="field-hint">
            Lệnh được gọi trong thư mục workspace độc lập của lần chạy trên Runner PC.
          </span>
        </div>

        <div className="form-group">
          <label htmlFor="version-contract" className="form-label">
            Contract Version
          </label>
          <input
            id="version-contract"
            type="text"
            className="form-input"
            value={contractVersion}
            onChange={(e) => setContractVersion(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="version-input-schema" className="form-label">
            Input JSON Schema
          </label>
          <textarea
            id="version-input-schema"
            className="form-textarea code-font"
            rows={5}
            value={inputSchemaStr}
            onChange={(e) => setInputSchemaStr(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="version-output-schema" className="form-label">
            Output JSON Schema
          </label>
          <textarea
            id="version-output-schema"
            className="form-textarea code-font"
            rows={5}
            value={outputSchemaStr}
            onChange={(e) => setOutputSchemaStr(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="form-actions">
          <button type="button" className="secondary-btn" onClick={onCancel} disabled={loading}>
            Hủy
          </button>
          <button type="submit" className="primary-btn" disabled={loading}>
            {loading ? "Đang lưu..." : "Lưu"}
          </button>
        </div>
      </form>
    </div>
  );
};
