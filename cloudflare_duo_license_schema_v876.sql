-- RemiX Duo V8.76 Cloudflare D1. Apply on a NEW dedicated D1 database.
-- Admin issues keys centrally; clients never receive the admin token or signing key.
CREATE TABLE IF NOT EXISTS license_keys (
  id TEXT PRIMARY KEY,
  key_sha256 TEXT NOT NULL UNIQUE,
  order_id TEXT NOT NULL,
  customer TEXT NOT NULL,
  edition TEXT NOT NULL CHECK(edition='DUO_PRO'),
  status TEXT NOT NULL CHECK(status IN ('ACTIVE','REVOKED')),
  max_seats INTEGER NOT NULL CHECK(max_seats BETWEEN 1 AND 500),
  issued_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS activations (
  id TEXT PRIMARY KEY,
  license_id TEXT NOT NULL REFERENCES license_keys(id),
  machine_id TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  last_seen_at INTEGER NOT NULL,
  UNIQUE(license_id,machine_id)
);
CREATE INDEX IF NOT EXISTS idx_license_orders ON license_keys(order_id);
CREATE INDEX IF NOT EXISTS idx_activations_license ON activations(license_id);
CREATE TRIGGER IF NOT EXISTS guard_license_seats
BEFORE INSERT ON activations
FOR EACH ROW
WHEN (SELECT COUNT(*) FROM activations WHERE license_id = NEW.license_id)
     >= (SELECT max_seats FROM license_keys WHERE id = NEW.license_id)
BEGIN
  SELECT RAISE(ABORT, 'LICENSE_SEAT_LIMIT');
END;
