import React, { useEffect, useState } from "react";
import type { Robot, RobotStatistics } from "./types";
import { deleteRobot, fetchRobots, fetchRobotStatistics } from "./api";
import { Confirm } from "../../shared/ui";

interface RobotListProps {
  onSelectRobot: (robotId: string) => void;
  onNewRobot: () => void;
  onEditRobot: (robot: Robot) => void;
  onNewVersion: (robotId: string) => void;
}

export const RobotList: React.FC<RobotListProps> = ({
  onSelectRobot,
  onNewRobot,
  onEditRobot,
  onNewVersion,
}) => {
  const [robots, setRobots] = useState<Robot[]>([]);
  const [statsMap, setStatsMap] = useState<Record<string, RobotStatistics>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<Robot | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchRobots("active");
      setRobots(list);
      // Fetch statistics for each robot to display version success rate
      const newStats: Record<string, RobotStatistics> = {};
      await Promise.all(
        list.map(async (r) => {
          try {
            const s = await fetchRobotStatistics(r.id);
            newStats[r.id] = s;
          } catch {
            // Non-blocking
          }
        })
      );
      setStatsMap(newStats);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <>
      <div className="page-heading">
        <h1>Robots</h1>
        <div className="row-actions">
          <button className="btn btn-primary" onClick={onNewRobot}>
            + Thêm Robot mới
          </button>
        </div>
      </div>

      <section className="panel">

      {error && <div className="error-box">{error}</div>}
      {loading && <div className="loading-indicator">Đang tải danh mục Robot...</div>}

      {!loading && robots.length === 0 && (
        <div className="empty-state">
          <p>Không có robot nào phù hợp.</p>
        </div>
      )}

      {!loading && robots.length > 0 && (
        <div className="table-responsive">
          <table className="runs-table">
            <thead>
              <tr>
                <th>Tên Robot</th>
                <th>Mô tả</th>
                <th>Active Version</th>
                <th>Tỷ lệ thành công</th>
                <th>Trạng thái</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {robots.map((robot) => {
                const stats = statsMap[robot.id]?.overall;
                const successRate = stats?.success_rate;
                return (
                  <tr key={robot.id} className="run-row" onClick={() => onSelectRobot(robot.id)}>
                    <td className="bold-cell">
                      <button className="link-button" onClick={() => onSelectRobot(robot.id)}>
                        {robot.name}
                      </button>
                    </td>
                    <td>{robot.description || "—"}</td>
                    <td>
                      {robot.active_version ? (
                        <span className="version-tag">
                          v{robot.active_version.version_number} 
                        </span>
                      ) : (
                        <span className="text-muted">Chưa có</span>
                      )}
                    </td>
                    <td>
                      {successRate !== null && successRate !== undefined ? (
                        <span
                          className={`badge ${
                            successRate >= 80
                              ? "badge-success"
                              : successRate >= 50
                                ? "badge-warning"
                                : "badge-failed"
                          }`}
                        >
                          {successRate}%
                        </span>
                      ) : (
                        <span className="badge badge-neutral">Chưa có dữ liệu</span>
                      )}
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          robot.status === "active" ? "badge-success" : "badge-neutral"
                        }`}
                      >
                        {robot.status === "active" ? "Hoạt động" : "Dữ liệu cũ"}
                      </span>
                    </td>
                    <td className="actions-cell" onClick={(e) => e.stopPropagation()}>
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => onSelectRobot(robot.id)}
                      >
                        Chi tiết
                      </button>
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => onEditRobot(robot)}
                      >
                        Sửa
                      </button>
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => onNewVersion(robot.id)}
                      >
                        + Version
                      </button>
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={(event) => {
                          event.stopPropagation();
                          setDeleting(robot);
                        }}
                      >
                        Xóa
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      </section>
      {deleting && (
        <Confirm title={`Xóa ${deleting.name}?`} onClose={() => setDeleting(null)} onConfirm={async () => {
          await deleteRobot(deleting.id);
          await loadData();
        }}>
          Chỉ xóa được Robot chưa có phiên bản đã phát hành và không được Process tham chiếu.
          Nếu bị chặn, thông báo sẽ nêu phiên bản hoặc Process liên quan.
        </Confirm>
      )}
    </>
  );
};
