import React, { useEffect, useState } from "react";
import type { Robot, RobotVersion } from "./types";
import { createRobot, fetchRobotVersions, updateRobot } from "./api";

interface RobotFormProps {
  initialRobot?: Robot | null;
  onSuccess: (robot: Robot) => void;
  onCancel: () => void;
}

export const RobotForm: React.FC<RobotFormProps> = ({ initialRobot, onSuccess, onCancel }) => {
  const isEditing = Boolean(initialRobot);
  const [name, setName] = useState(initialRobot?.name || "");
  const [description, setDescription] = useState(initialRobot?.description || "");
  const [activeVersionId, setActiveVersionId] = useState(initialRobot?.active_version_id || "");
  const [versions, setVersions] = useState<RobotVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialRobot?.id) {
      fetchRobotVersions(initialRobot.id)
        .then((vList) => {
          // Only published versions can be set as active
          setVersions(vList.filter((v) => v.status === "published"));
        })
        .catch(() => {});
    }
  }, [initialRobot]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Tên Robot không được để trống");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      if (isEditing && initialRobot) {
        const updated = await updateRobot(initialRobot.id, {
          name: name.trim(),
          description: description.trim(),
          active_version_id: activeVersionId || null,
        });
        onSuccess(updated);
      } else {
        const created = await createRobot({
          name: name.trim(),
          description: description.trim(),
        });
        onSuccess(created);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="run-form-card">
      <div className="form-header">
        <h3>{isEditing ? `Chỉnh sửa Robot: ${initialRobot?.name}` : "Tạo Robot mới"}</h3>
        <p className="form-hint">
          Robot là chương trình tự động độc lập. Tên và metadata được quản lý trong catalog; việc gán Agent phụ trách và PC thực thi nằm tại từng node trong Process.
        </p>
      </div>

      {error && <div className="error-box">{error}</div>}

      <form onSubmit={handleSubmit} className="standard-form">
        <div className="form-group">
          <label htmlFor="robot-name" className="form-label">
            Tên Robot <span className="required">*</span>
          </label>
          <input
            id="robot-name"
            type="text"
            className="form-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ví dụ: Audio Transcription Robot"
            disabled={loading}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="robot-desc" className="form-label">
            Mô tả
          </label>
          <textarea
            id="robot-desc"
            className="form-textarea"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Mô tả chức năng, định dạng đầu vào/đầu ra mong muốn..."
            disabled={loading}
          />
        </div>

        {isEditing && (
          <div className="form-group">
            <label htmlFor="robot-active-version" className="form-label">
              Active Version (Phiên bản mặc định khi thêm node mới)
            </label>
            <select
              id="robot-active-version"
              className="form-select"
              value={activeVersionId}
              onChange={(e) => setActiveVersionId(e.target.value)}
              disabled={loading}
            >
              <option value="">-- Chưa chọn (None) --</option>
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version_number} - {v.entrypoint} (Contract: {v.contract_version})
                </option>
              ))}
            </select>
            <span className="field-hint">
              Chọn phiên bản mặc định cho Robot. Các bước và lần chạy đã cấu hình vẫn giữ đúng phiên bản đã chọn.
            </span>
          </div>
        )}

        <div className="form-actions">
          <button type="button" className="secondary-btn" onClick={onCancel} disabled={loading}>
            Hủy
          </button>
          <button type="submit" className="primary-btn" disabled={loading}>
            {loading ? "Đang lưu..." : isEditing ? "Lưu thay đổi" : "Tạo Robot"}
          </button>
        </div>
      </form>
    </div>
  );
};
