"""Narrow, transaction-local exception for explicitly requested aggregate deletion."""


def delete_rows(connection, table: str, where: str, parameters=()):
    # Callers supply internal SQL constants only, never user-selected table names/SQL.
    # No trigger is dropped and no foreign key is disabled at runtime. Permit only
    # rows already selected by this deletion on this connection, for one statement.
    rowids = {row[0] for row in connection.execute(f"SELECT rowid FROM {table} WHERE {where}", parameters)}
    connection.create_function("cf_delete_allowed", 2, lambda name, rowid: int(name == table and rowid in rowids))
    try:
        return connection.execute(f"DELETE FROM {table} WHERE {where}", parameters)
    finally:
        connection.create_function("cf_delete_allowed", 2, lambda name, rowid: 0)
