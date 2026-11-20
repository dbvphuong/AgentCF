"""Retry deletion of uploaded Server objects after the owning DB transaction commits."""

import logging


def cleanup_artifacts(database, storage_dir):
    root = storage_dir.resolve()
    with database.connect() as conn:
        keys = [r[0] for r in conn.execute("SELECT storage_key FROM artifact_cleanup")]
    for key in keys:
        try:
            target = (root / key).resolve()
            if target == root or not target.is_relative_to(root):
                raise ValueError("Artifact path is outside Server storage")
            target.unlink(missing_ok=True)
            with database.transaction() as conn:
                conn.execute("DELETE FROM artifact_cleanup WHERE storage_key=?", (key,))
        except (OSError, ValueError):
            # Leave the durable request for the next startup/deletion, never touch PC output.
            logging.getLogger(__name__).warning("Server artifact cleanup pending")
