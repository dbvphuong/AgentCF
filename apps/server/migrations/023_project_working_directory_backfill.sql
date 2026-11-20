-- Preserve the existing workspace when removing the node-level cwd control.
-- Only fill empty Projects when all current saved node roots agree.
WITH process_sources AS (
    SELECT p.project_id,
        CASE WHEN EXISTS (
            SELECT 1 FROM json_each(p.configuration_json, '$.tasks') node
            WHERE json_extract(node.value, '$.kind') = 'agent'
              AND trim(COALESCE(json_extract(node.value, '$.working_directory'), '')) <> ''
        ) THEN p.configuration_json ELSE (
            SELECT definition_json FROM process_versions v
            WHERE v.process_id = p.id ORDER BY version_number DESC LIMIT 1
        ) END AS definition_json
    FROM processes p
), roots AS (
    SELECT project_id, trim(json_extract(node.value, '$.working_directory')) AS root
    FROM process_sources, json_each(definition_json, '$.tasks') node
    WHERE json_extract(node.value, '$.kind') = 'agent'
      AND json_type(node.value, '$.working_directory') = 'text'
      AND trim(json_extract(node.value, '$.working_directory')) <> ''
), compatible AS (
    SELECT project_id, MIN(root) AS root FROM roots
    GROUP BY project_id
    HAVING COUNT(DISTINCT lower(rtrim(root, '/\'))) = 1
       AND MIN(CASE WHEN substr(root, 1, 1) = '/'
                     OR substr(root, 1, 2) = '\\'
                     OR (substr(root, 2, 1) = ':' AND substr(root, 3, 1) IN ('/', '\'))
                    THEN 1 ELSE 0 END) = 1
)
UPDATE projects SET working_directory = compatible.root
FROM compatible
WHERE projects.id = compatible.project_id
  AND trim(COALESCE(projects.working_directory, '')) = '';
