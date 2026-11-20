ALTER TABLE task_runs ADD COLUMN queued_at TEXT;

ALTER TABLE task_runs ADD COLUMN queue_deadline_at TEXT;

CREATE TRIGGER event_attempt_matches_task BEFORE INSERT ON run_events
WHEN NEW.attempt_id IS NOT NULL AND NEW.task_run_id IS NOT NULL
    AND NOT EXISTS(SELECT 1 FROM attempts WHERE id = NEW.attempt_id AND task_run_id = NEW.task_run_id AND run_id = NEW.run_id)
BEGIN
    SELECT RAISE(ABORT, 'event_attempt_task_mismatch');
END;

CREATE TRIGGER terminal_run_requires_settled_tasks BEFORE UPDATE OF status ON process_runs
WHEN NEW.status IN ('succeeded', 'failed', 'cancelled') AND (
    EXISTS(SELECT 1 FROM task_runs WHERE run_id = NEW.id AND status NOT IN ('succeeded', 'failed', 'skipped', 'cancelled'))
    OR EXISTS(SELECT 1 FROM attempts WHERE run_id = NEW.id AND status NOT IN ('succeeded', 'failed', 'cancelled'))
    OR (NEW.status = 'succeeded' AND EXISTS(SELECT 1 FROM task_runs WHERE run_id = NEW.id AND status <> 'succeeded'))
)
BEGIN
    SELECT RAISE(ABORT, 'run_tasks_unsettled');
END;

CREATE TRIGGER immutable_run_delete BEFORE DELETE ON process_runs
BEGIN
    SELECT RAISE(ABORT, 'run_history_immutable');
END;

CREATE TRIGGER immutable_task_run_delete BEFORE DELETE ON task_runs
BEGIN
    SELECT RAISE(ABORT, 'task_run_history_immutable');
END;

CREATE TRIGGER immutable_attempt_delete BEFORE DELETE ON attempts
BEGIN
    SELECT RAISE(ABORT, 'attempt_history_immutable');
END;

CREATE TRIGGER finalized_artifact_delete BEFORE DELETE ON artifacts
WHEN OLD.availability = 'available'
BEGIN
    SELECT RAISE(ABORT, 'artifact_immutable');
END;

CREATE TRIGGER immutable_grant_identity BEFORE UPDATE ON execution_grants
WHEN NEW.attempt_id <> OLD.attempt_id OR NEW.task_run_id <> OLD.task_run_id
    OR NEW.runner_id <> OLD.runner_id OR NEW.session_id <> OLD.session_id
    OR NEW.generation <> OLD.generation OR NEW.token_hash <> OLD.token_hash
BEGIN
    SELECT RAISE(ABORT, 'grant_identity_immutable');
END;

CREATE TRIGGER immutable_receipt_update BEFORE UPDATE ON receipts
BEGIN
    SELECT RAISE(ABORT, 'receipt_immutable');
END;

CREATE TRIGGER immutable_receipt_delete BEFORE DELETE ON receipts
BEGIN
    SELECT RAISE(ABORT, 'receipt_immutable');
END;

CREATE TRIGGER immutable_inbox_update BEFORE UPDATE ON engine_inbox
BEGIN
    SELECT RAISE(ABORT, 'inbox_immutable');
END;

CREATE TRIGGER immutable_inbox_delete BEFORE DELETE ON engine_inbox
BEGIN
    SELECT RAISE(ABORT, 'inbox_immutable');
END;

CREATE TRIGGER immutable_outbox_command BEFORE UPDATE ON engine_outbox
WHEN NEW.command_id <> OLD.command_id OR NEW.run_id <> OLD.run_id OR NEW.sequence <> OLD.sequence
    OR NEW.command_type <> OLD.command_type OR NEW.payload_json <> OLD.payload_json
    OR NEW.created_at <> OLD.created_at
BEGIN
    SELECT RAISE(ABORT, 'outbox_command_immutable');
END;
