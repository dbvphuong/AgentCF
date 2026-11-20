ALTER TABLE runner_pairing_codes ADD COLUMN id TEXT;
ALTER TABLE runner_pairing_codes ADD COLUMN runner_id TEXT REFERENCES runners(id);
CREATE UNIQUE INDEX runner_pairing_codes_id ON runner_pairing_codes(id) WHERE id IS NOT NULL;
ALTER TABLE runners ADD COLUMN os_name TEXT;
