CREATE TABLE robots (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK(length(trim(name)) > 0),
    description TEXT NOT NULL DEFAULT '',
    active_version_id TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'archived')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE TABLE robot_versions (
    id TEXT PRIMARY KEY,
    robot_id TEXT NOT NULL REFERENCES robots(id),
    version_number INTEGER NOT NULL CHECK(version_number > 0),
    status TEXT NOT NULL CHECK(status IN ('draft', 'published')),
    contract_version TEXT NOT NULL DEFAULT '1.0.0' CHECK(length(trim(contract_version)) > 0),
    entrypoint TEXT NOT NULL CHECK(length(trim(entrypoint)) > 0),
    input_schema_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(input_schema_json)),
    output_schema_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(output_schema_json)),
    bundle_sha256 TEXT CHECK(bundle_sha256 IS NULL OR (length(bundle_sha256) = 64 AND bundle_sha256 NOT GLOB '*[^a-f0-9]*')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    published_at TEXT,
    UNIQUE(robot_id, version_number),
    CHECK(status = 'draft' OR (bundle_sha256 IS NOT NULL AND published_at IS NOT NULL))
) STRICT;

CREATE UNIQUE INDEX one_draft_per_robot ON robot_versions(robot_id) WHERE status = 'draft';

CREATE TRIGGER immutable_published_robot_version_update BEFORE UPDATE ON robot_versions
WHEN OLD.status = 'published'
BEGIN
    SELECT RAISE(ABORT, 'published_robot_version_immutable');
END;

CREATE TRIGGER immutable_published_robot_version_delete BEFORE DELETE ON robot_versions
WHEN OLD.status = 'published'
BEGIN
    SELECT RAISE(ABORT, 'published_robot_version_immutable');
END;
