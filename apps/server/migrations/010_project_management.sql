ALTER TABLE projects ADD COLUMN description TEXT NOT NULL DEFAULT '';
ALTER TABLE projects ADD COLUMN pm_agent_id TEXT REFERENCES agents(id);
ALTER TABLE processes ADD COLUMN description TEXT NOT NULL DEFAULT '';

CREATE TABLE project_team (
    project_id TEXT NOT NULL REFERENCES projects(id),
    agent_id TEXT NOT NULL REFERENCES agents(id),
    PRIMARY KEY(project_id, agent_id)
) STRICT;

ALTER TABLE project_targets ADD COLUMN starts_on TEXT;
ALTER TABLE project_targets ADD COLUMN ends_on TEXT;
ALTER TABLE project_targets ADD COLUMN acceptance_criteria TEXT NOT NULL DEFAULT '';
