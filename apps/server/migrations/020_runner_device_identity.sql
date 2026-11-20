ALTER TABLE runners ADD COLUMN device_id TEXT;
ALTER TABLE runners ADD COLUMN device_key_hash TEXT;
CREATE UNIQUE INDEX one_active_pc_per_device ON runners(workspace_id, device_id)
WHERE device_id IS NOT NULL AND deleted_at IS NULL;
ALTER TABLE runner_pairing_codes ADD COLUMN target_runner_id TEXT REFERENCES runners(id);
