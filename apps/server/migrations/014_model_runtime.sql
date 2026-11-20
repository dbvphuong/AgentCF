ALTER TABLE models ADD COLUMN runtime_adapter TEXT CHECK(runtime_adapter IS NULL OR runtime_adapter IN ('codex','antigravity'));
