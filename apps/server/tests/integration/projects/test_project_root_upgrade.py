"""Removing a node control must preserve an existing unambiguous workspace."""
import json

import pytest

from agent_cf_server.infrastructure.persistence.database import Database


@pytest.mark.parametrize("source", ["configuration", "legacy"])
def test_existing_node_root_moves_to_project_without_changing_snapshots(tmp_path, source):
    db=Database(tmp_path / "upgrade.sqlite3")
    db.migrate(target_version=22)
    graph={"tasks":[{"id":"one","kind":"agent","working_directory":r"E:\Project"}]}
    raw=json.dumps(graph)
    with db.transaction() as conn:
        conn.execute("INSERT INTO workspaces(id,name) VALUES ('w','Workspace')")
        for pid, root in [("empty",""),("explicit",r"E:\Chosen"),("conflict",""),("unknown","")]:
            conn.execute("INSERT INTO projects(id,workspace_id,name,working_directory) VALUES (?,'w',?,?)",(pid,pid,root))
        for pid in ["empty","explicit","conflict"]:
            conn.execute("INSERT INTO processes(id,project_id,name,configuration_json) VALUES (?,?,?,?)",(pid,pid,pid,raw if source=="configuration" else None))
            conn.execute("INSERT INTO process_versions(id,process_id,version_number,status,definition_format_version,interpreter_version,definition_json) VALUES (?,?,1,'draft','1','dag-v1',?)",(pid,pid,raw))
        other=json.dumps({"tasks":[{"kind":"agent","working_directory":r"E:\Other"}]})
        conn.execute("INSERT INTO processes(id,project_id,name,configuration_json) VALUES ('other','conflict','Other',?)",(other,))
    db.migrate()
    with db.connect() as conn:
        roots=dict(conn.execute("SELECT id,working_directory FROM projects"))
        assert roots=={"empty":r"E:\Project","explicit":r"E:\Chosen","conflict":"","unknown":""}
        assert conn.execute("SELECT definition_json FROM process_versions WHERE id='empty'").fetchone()[0]==raw
        if source=="configuration":
            assert conn.execute("SELECT configuration_json FROM processes WHERE id='empty'").fetchone()[0]==raw
