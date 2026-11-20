ALTER TABLE runners ADD COLUMN memory_total_bytes INTEGER CHECK(memory_total_bytes IS NULL OR memory_total_bytes > 0);
ALTER TABLE runners ADD COLUMN memory_used_bytes INTEGER CHECK(memory_used_bytes IS NULL OR memory_used_bytes >= 0);
