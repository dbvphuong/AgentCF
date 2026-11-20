import React, { useEffect, useState } from "react";
import type { Robot, RobotStatistics, RobotVersion } from "./types";
import {
  fetchRobot,
  fetchRobotStatistics,
  fetchRobotVersions,
  publishRobotVersion,
  updateRobot,
} from "./api";

interface RobotDetailProps {
  robotId: string;
  onBack: () => void;
  onEdit: (robot: Robot) => void;
  onNewVersion: (robotId: string) => void;
}

export const RobotDetail: React.FC<RobotDetailProps> = ({
  robotId,
  onBack,
  onEdit,
  onNewVersion,
}) => {
  const [robot, setRobot] = useState<Robot | null>(null);
  const [versions, setVersions] = useState<RobotVersion[]>([]);
  const [stats, setStats] = useState<RobotStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [rData, vData, sData] = await Promise.all([
        fetchRobot(robotId),
        fetchRobotVersions(robotId),
        fetchRobotStatistics(robotId),
      ]);
      setRobot(rData);
      setVersions(vData);
      setStats(sData);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, [robotId]);

  const handleSetActive = async (version: RobotVersion) => {
    setActionLoading(true);
    try {
      if (version.status !== "published") await publishRobotVersion(robotId, version.id);
      await updateRobot(robotId, { active_version_id: version.id });
      await loadAll();
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err));
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return <div className="loading-indicator">Đang tải thông tin Robot...</div>;
  }

  if (error || !robot) {
    return (
      <div className="runs-container">
        <div className="error-box">{error || "Không tìm thấy Robot"}</div>
        <button className="secondary-btn" onClick={onBack}>
          Quay lại danh sách
        </button>
      </div>
    );
  }

  const overall = stats?.overall;

  return (
    <div className="runs-container">
      <div className="runs-header">
        <div>
          <button className="link-back-btn" onClick={onBack}>
            &larr; Quay lại danh mục
          </button>
          <h2>{robot.name}</h2>
          <p className="runs-subtitle">{robot.description || "Chưa có mô tả"}</p>
        </div>
        <div className="header-actions">
          <button className="secondary-btn" onClick={() => onEdit(robot)}>
            Chỉnh sửa
          </button>
          <button className="primary-btn" onClick={() => onNewVersion(robot.id)}>
            + Tạo Version mới
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid-cards-3">
        <div className="summary-card">
          <span className="card-label">Trạng thái</span>
          <span className={`badge ${robot.status === "active" ? "badge-succeeded" : "badge-cancelled"}`}>
            {robot.status === "active" ? "Hoạt động" : "Dữ liệu cũ"}
          </span>
        </div>

        <div className="summary-card">
          <span className="card-label">Active Version</span>
          <span className="card-value">
            {robot.active_version ? `v${robot.active_version.version_number}` : "Chưa chọn"}
          </span>
        </div>

        <div className="summary-card">
          <span className="card-label">Tỷ lệ thành công (Toàn bộ)</span>
          <span className="card-value">
            {overall?.success_rate !== null && overall?.success_rate !== undefined ? (
              <span className="text-succeeded">{overall.success_rate}%</span>
            ) : (
              <span className="text-muted">Chưa có dữ liệu</span>
            )}
          </span>
        </div>
      </div>

      {/* Execution Statistics Breakdown */}
      <div className="run-detail-card" style={{ marginTop: "1rem" }}>
        <h4>Thống kê thực thi thực tế</h4>
        <div className="stats-metric-row">
          <div className="metric-box">
            <span className="metric-num">{overall?.total_runs || 0}</span>
            <span className="metric-title">Tổng lần chạy</span>
          </div>
          <div className="metric-box">
            <span className="metric-num text-succeeded">{overall?.succeeded_runs || 0}</span>
            <span className="metric-title">Thành công</span>
          </div>
          <div className="metric-box">
            <span className="metric-num text-failed">{overall?.failed_runs || 0}</span>
            <span className="metric-title">Thất bại (kể cả Timeout)</span>
          </div>
          <div className="metric-box">
            <span className="metric-num text-cancelled">{overall?.cancelled_runs || 0}</span>
            <span className="metric-title">Đã hủy</span>
          </div>
        </div>
      </div>

      {/* Version Table */}
      <div className="run-detail-card" style={{ marginTop: "1rem" }}>
        <h4>Danh sách các phiên bản ({versions.length})</h4>
        {versions.length === 0 ? (
          <p className="text-muted">Robot này chưa có phiên bản nào. Hãy tạo phiên bản đầu tiên.</p>
        ) : (
          <div className="table-responsive">
            <table className="runs-table">
              <thead>
                <tr>
                  <th>Phiên bản</th>
                  <th>Trạng thái</th>
                  <th>Entrypoint</th>
                  <th>Contract</th>
                  <th>Tỷ lệ thành công</th>
                  <th>Tổng / Thành công / Lỗi</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {versions.map((ver) => {
                  const vStat = stats?.versions.find((v) => v.robot_version_id === ver.id);
                  const isActive = robot.active_version_id === ver.id;
                  const vSuccessRate = vStat?.success_rate;

                  return (
                    <tr key={ver.id} className={isActive ? "row-highlight" : ""}>
                      <td className="bold-cell">
                        v{ver.version_number} {isActive && <span className="active-tag">(Active)</span>}
                      </td>
                      <td>
                        <span className={`badge ${ver.status === "published" ? "badge-succeeded" : "badge-queued"}`}>
                          {ver.status === "published" ? "Sẵn sàng" : "Chưa dùng"}
                        </span>
                      </td>
                      <td>
                        <code>{ver.entrypoint}</code>
                      </td>
                      <td>{ver.contract_version}</td>
                      <td>
                        {vSuccessRate !== null && vSuccessRate !== undefined ? (
                          <span className="badge badge-succeeded">{vSuccessRate}%</span>
                        ) : (
                          <span className="badge badge-neutral">Chưa có dữ liệu</span>
                        )}
                      </td>
                      <td>
                        {vStat ? `${vStat.total_runs} / ${vStat.succeeded_runs} / ${vStat.failed_runs}` : "0 / 0 / 0"}
                      </td>
                      <td className="actions-cell">
                        {!isActive && (
                          <button
                            className="small-btn"
                            onClick={() => handleSetActive(ver)}
                            disabled={actionLoading}
                          >
                            Dùng phiên bản này
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
