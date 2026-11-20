CREATE TABLE workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK(length(trim(name)) > 0)
) STRICT;

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'archived')),
    UNIQUE(id, workspace_id)
) STRICT;

CREATE TABLE processes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'archived')),
    UNIQUE(id, project_id)
) STRICT;

CREATE TABLE process_versions (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL REFERENCES processes(id),
    version_number INTEGER NOT NULL CHECK(version_number > 0),
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    status TEXT NOT NULL CHECK(status IN ('draft', 'published')),
    definition_format_version TEXT NOT NULL,
    interpreter_version TEXT NOT NULL,
    definition_json TEXT NOT NULL CHECK(json_valid(definition_json)),
    snapshot_sha256 TEXT CHECK(length(snapshot_sha256) = 64 AND snapshot_sha256 NOT GLOB '*[^a-f0-9]*'),
    published_at TEXT,
    UNIQUE(process_id, version_number),
    UNIQUE(id, process_id),
    CHECK(status = 'draft' OR (snapshot_sha256 IS NOT NULL AND published_at IS NOT NULL))
) STRICT;

CREATE UNIQUE INDEX one_draft_per_process ON process_versions(process_id) WHERE status = 'draft';

CREATE TABLE tasks (
    process_version_id TEXT NOT NULL REFERENCES process_versions(id),
    id TEXT NOT NULL,
    task_key TEXT NOT NULL,
    definition_json TEXT NOT NULL CHECK(json_valid(definition_json)),
    PRIMARY KEY(process_version_id, id),
    UNIQUE(process_version_id, task_key)
) STRICT;

CREATE TABLE dependencies (
    process_version_id TEXT NOT NULL,
    source_task_id TEXT NOT NULL,
    target_task_id TEXT NOT NULL,
    PRIMARY KEY(process_version_id, source_task_id, target_task_id),
    FOREIGN KEY(process_version_id, source_task_id) REFERENCES tasks(process_version_id, id),
    FOREIGN KEY(process_version_id, target_task_id) REFERENCES tasks(process_version_id, id),
    CHECK(source_task_id <> target_task_id)
) STRICT;

CREATE TRIGGER immutable_published_version_update BEFORE UPDATE ON process_versions
WHEN OLD.status = 'published'
BEGIN
    SELECT RAISE(ABORT, 'published_version_immutable');
END;

CREATE TRIGGER immutable_published_version_delete BEFORE DELETE ON process_versions
WHEN OLD.status = 'published'
BEGIN
    SELECT RAISE(ABORT, 'published_version_immutable');
END;

CREATE TRIGGER immutable_published_task_insert BEFORE INSERT ON tasks
WHEN (SELECT status FROM process_versions WHERE id = NEW.process_version_id) = 'published'
BEGIN
    SELECT RAISE(ABORT, 'published_version_immutable');
END;

CREATE TRIGGER immutable_published_task_update BEFORE UPDATE ON tasks
WHEN (SELECT status FROM process_versions WHERE id = OLD.process_version_id) = 'published'
  OR (SELECT status FROM process_versions WHERE id = NEW.process_version_id) = 'published'
BEGIN
    SELECT RAISE(ABORT, 'published_version_immutable');
END;

CREATE TRIGGER immutable_published_task_delete BEFORE DELETE ON tasks
WHEN (SELECT status FROM process_versions WHERE id = OLD.process_version_id) = 'published'
BEGIN
    SELECT RAISE(ABORT, 'published_version_immutable');
END;

CREATE TRIGGER immutable_published_dependency_insert BEFORE INSERT ON dependencies
WHEN (SELECT status FROM process_versions WHERE id = NEW.process_version_id) = 'published'
BEGIN
    SELECT RAISE(ABORT, 'published_version_immutable');
END;

CREATE TRIGGER immutable_published_dependency_update BEFORE UPDATE ON dependencies
WHEN (SELECT status FROM process_versions WHERE id = OLD.process_version_id) = 'published'
  OR (SELECT status FROM process_versions WHERE id = NEW.process_version_id) = 'published'
BEGIN
    SELECT RAISE(ABORT, 'published_version_immutable');
END;

CREATE TRIGGER immutable_published_dependency_delete BEFORE DELETE ON dependencies
WHEN (SELECT status FROM process_versions WHERE id = OLD.process_version_id) = 'published'
BEGIN
    SELECT RAISE(ABORT, 'published_version_immutable');
END;
