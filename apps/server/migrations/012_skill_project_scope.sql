ALTER TABLE skills ADD COLUMN is_global INTEGER NOT NULL DEFAULT 1 CHECK(is_global IN (0,1));
CREATE TABLE skill_projects (
    skill_id TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id),
    PRIMARY KEY (skill_id, project_id)
) STRICT;
CREATE INDEX skill_projects_by_project ON skill_projects(project_id, skill_id);
