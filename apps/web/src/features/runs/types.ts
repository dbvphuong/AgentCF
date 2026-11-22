export type RunStatus =
  | "queued"
  | "running"
  | "reconciling"
  | "cancelling"
  | "succeeded"
  | "failed"
  | "cancelled";

export type TaskRunStatus =
  | "pending"
  | "queued"
  | "running"
  | "reconciling"
  | "succeeded"
  | "failed"
  | "skipped"
  | "cancelled";

export interface WaitingContext {
  session_id?: string | null;
  turn_number?: number;
  question?: string;
  suggested_options?: string[];
  summary_vi?: string;
}

export interface AgentTurnDecision {
  id: string;
  task_run_id: string;
  attempt_id: string;
  agent_id: string;
  turn_number: number;
  action: "done" | "reply" | "need_human" | "retry" | "fail";
  reply_message?: string | null;
  route?: string | null;
  summary_vi: string;
  question_for_user?: string | null;
  suggested_options?: string[];
  error_analysis?: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  created_at: string;
}

export interface TaskRun {
  id: string;
  run_id: string;
  process_version_id: string;
  task_id: string;
  task_key?: string;
  status: TaskRunStatus;
  generation: number;
  input?: Record<string, unknown> | null;
  output?: Record<string, unknown> | null;
  error?: Record<string, unknown> | null;
  waiting_for?: string | null;
  attention_reason?: string | null;
  waiting_context?: WaitingContext | null;
}

export interface ArtifactRef {
  id: string;
  attempt_id: string;
  logical_name: string;
  media_type: string;
  size_bytes: number;
  sha256: string;
  availability: "uploading" | "available";
  storage_key: string;
  created_at: string;
}

export interface Run {
  id: string;
  workspace_id: string;
  project_id: string;
  process_id: string;
  process_version_id: string;
  process_name?: string;
  snapshot_sha256: string;
  revision: number;
  status: RunStatus;
  input: Record<string, unknown>;
  output?: Record<string, unknown> | null;
  error?: Record<string, unknown> | null;
  attention_reason?: string | null;
  created_at: string;
  started_at?: string | null;
  ended_at?: string | null;
  queue_deadline_at: string;
  task_runs: TaskRun[];
  turn_decisions?: AgentTurnDecision[];
  artifacts?: ArtifactRef[];
}

export interface RunEvent {
  id: string;
  run_id: string;
  sequence: number;
  event_type: string;
  task_run_id?: string | null;
  attempt_id?: string | null;
  data: Record<string, unknown>;
  recorded_at: string;
}

export interface CreateRunPayload {
  process_version_id: string;
  input: Record<string, unknown>;
  default_runner_id?: string;
}
