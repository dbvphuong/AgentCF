"""Delete one Project/Process aggregate, including its completed execution history."""

from agent_cf_server.infrastructure.persistence.deletion import delete_rows


def delete_process_history(conn, column, resource_id):
    # column is chosen by ProjectManagement, not supplied by an HTTP client.
    runs = f"SELECT id FROM process_runs WHERE {column}=?"
    attempts = f"SELECT id FROM attempts WHERE run_id IN ({runs})"
    tasks = f"SELECT id FROM task_runs WHERE run_id IN ({runs})"
    processes = "SELECT id FROM processes WHERE project_id=?" if column == "project_id" else "SELECT id FROM processes WHERE id=?"
    schedules = f"SELECT id FROM schedules WHERE {column}=?"
    conn.execute("CREATE TEMP TABLE deletion_resources(id TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO deletion_resources VALUES (?)", (resource_id,))
    for query in (processes, f"SELECT id FROM process_versions WHERE process_id IN ({processes})", runs, tasks, attempts, schedules):
        conn.execute(f"INSERT OR IGNORE INTO deletion_resources {query}", (resource_id,))
    conn.execute(
        f"INSERT OR IGNORE INTO artifact_cleanup(storage_key) SELECT storage_key FROM artifacts WHERE attempt_id IN ({attempts})",
        (resource_id,),
    )
    for table, where, parameters in (
        ("receipts", "resource_id IN (SELECT id FROM deletion_resources) OR json_extract(response_json,'$.id') IN (SELECT id FROM deletion_resources)", ()),
        ("audit_events", f"run_id IN ({runs}) OR resource_id IN (SELECT id FROM deletion_resources)", (resource_id,)),
        ("run_events", f"run_id IN ({runs})", (resource_id,)),
        ("engine_inbox", f"run_id IN ({runs})", (resource_id,)),
        ("engine_outbox", f"run_id IN ({runs})", (resource_id,)),
        ("human_decisions", f"run_id IN ({runs})", (resource_id,)),
        ("agent_turn_decisions", f"run_id IN ({runs})", (resource_id,)),
        ("review_decisions", f"task_run_id IN ({tasks})", (resource_id,)),
        ("run_error_acknowledgments", f"run_id IN ({runs})", (resource_id,)),
        ("agent_token_usage", f"run_id IN ({runs})", (resource_id,)),
        ("schedule_ticks", f"run_id IN ({runs}) OR schedule_id IN ({schedules})", (resource_id, resource_id)),
        ("schedules", f"{column}=?", (resource_id,)),
        ("artifacts", f"attempt_id IN ({attempts})", (resource_id,)),
        ("execution_grants", f"attempt_id IN ({attempts})", (resource_id,)),
        ("attempts", f"run_id IN ({runs})", (resource_id,)),
        ("task_runs", f"run_id IN ({runs})", (resource_id,)),
        ("process_runs", f"{column}=?", (resource_id,)),
        ("dependencies", f"process_version_id IN (SELECT id FROM process_versions WHERE process_id IN ({processes}))", (resource_id,)),
        ("tasks", f"process_version_id IN (SELECT id FROM process_versions WHERE process_id IN ({processes}))", (resource_id,)),
        ("process_versions", f"process_id IN ({processes})", (resource_id,)),
        ("processes", f"id IN ({processes})", (resource_id,)),
    ):
        delete_rows(conn, table, where, parameters)
    conn.execute("DROP TABLE deletion_resources")
