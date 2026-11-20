export interface UnresolvedError {
  run_id: string;
  project_id: string;
  project_name: string;
  process_id: string;
  process_name: string;
  process_version_id: string;
  error?: Record<string, unknown> | null;
  topic?: string | null;
  occurred_at: string;
}

export interface ProjectTarget {
  name: string;
  period: string;
  target_count: number;
  completed_count: number;
  status: string;
}

export interface ProjectProgress {
  project_id: string;
  name: string;
  targets: ProjectTarget[] | null;
  has_targets: boolean;
  total_runs: number;
  succeeded_runs: number;
  failed_runs: number;
  running_runs: number;
}

export interface AgentTokenUsage {
  agent_id: string;
  name: string;
  role_id: string;
  model_id: string;
  has_usage: boolean;
  total_tokens?: number | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
}

export interface OverviewSummaryData {
  unresolved_errors: UnresolvedError[];
  projects_progress: ProjectProgress[];
  agents_token_usage: AgentTokenUsage[];
  summary_stats: {
    unresolved_error_count: number;
    active_projects_count: number;
    active_agents_count: number;
  };
}
