ALTER TABLE processes ADD COLUMN configuration_json TEXT CHECK(configuration_json IS NULL OR json_valid(configuration_json));
ALTER TABLE processes ADD COLUMN configuration_revision INTEGER NOT NULL DEFAULT 0;
ALTER TABLE schedules ADD COLUMN follow_current_configuration INTEGER NOT NULL DEFAULT 1 CHECK(follow_current_configuration IN (0,1));
