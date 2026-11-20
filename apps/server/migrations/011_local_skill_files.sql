ALTER TABLE skill_versions ADD COLUMN source_path TEXT;
ALTER TABLE skill_versions ADD COLUMN source_runner_id TEXT REFERENCES runners(id);
