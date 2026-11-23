CREATE TABLE IF NOT EXISTS license_activations (
  id TEXT PRIMARY KEY,
  license_row_id TEXT NOT NULL,
  license_id TEXT NOT NULL,
  machine_hash TEXT NOT NULL,
  machine_label TEXT,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  app_version TEXT,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  released_at TEXT,
  revoked_at TEXT,
  note TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_license_activations_unique_machine
ON license_activations(license_row_id, machine_hash);

CREATE INDEX IF NOT EXISTS idx_license_activations_license_row
ON license_activations(license_row_id);

CREATE INDEX IF NOT EXISTS idx_license_activations_machine
ON license_activations(machine_hash);

CREATE INDEX IF NOT EXISTS idx_license_activations_last_seen
ON license_activations(last_seen_at);
