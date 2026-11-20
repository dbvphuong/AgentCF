export type RobotStatus = "active" | "archived";
export type VersionStatus = "draft" | "published";

export interface RobotVersion {
  id: string;
  robot_id: string;
  version_number: number;
  status: VersionStatus;
  contract_version: string;
  entrypoint: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  bundle_sha256?: string | null;
  created_at: string;
  published_at?: string | null;
}

export interface Robot {
  id: string;
  name: string;
  description: string;
  active_version_id?: string | null;
  active_version?: Partial<RobotVersion> | null;
  status: RobotStatus;
  created_at: string;
  updated_at: string;
}

export interface RobotVersionStatistics {
  robot_version_id: string;
  version_number: number;
  status: VersionStatus;
  entrypoint: string;
  published_at?: string | null;
  total_runs: number;
  succeeded_runs: number;
  failed_runs: number;
  cancelled_runs: number;
  success_rate: number | null; // null if no completed runs
}

export interface RobotOverallStatistics {
  total_runs: number;
  succeeded_runs: number;
  failed_runs: number;
  cancelled_runs: number;
  success_rate: number | null;
}

export interface RobotStatistics {
  robot_id: string;
  name: string;
  active_version_id?: string | null;
  overall: RobotOverallStatistics;
  versions: RobotVersionStatistics[];
}

export interface CreateRobotPayload {
  id?: string;
  name: string;
  description?: string;
  active_version_id?: string | null;
  status?: RobotStatus;
}

export interface UpdateRobotPayload {
  name?: string;
  description?: string;
  active_version_id?: string | null;
  status?: RobotStatus;
}

export interface CreateRobotVersionPayload {
  ready_to_use?: boolean;
  id?: string;
  entrypoint: string;
  contract_version?: string;
  input_schema?: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
}
