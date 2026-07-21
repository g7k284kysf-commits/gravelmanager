# Changelog

## 0.3.0 - 2026-07-21

### Added

- Tenant and membership foundation with existing-data backfill.
- Season, hierarchical goal and A/B/C competition planning APIs and UI.
- Capability-based provider registry and honest Garmin, TrainingPeaks and CORE placeholders.
- Encrypted connection records, durable sync state, correlation-aware audit events and Redis-backed jobs.
- Secure FIT, TCX, GPX and CSV uploads with normalized import records and duplicate detection.
- Integration settings, connection history and planning overview interfaces.

### Changed

- Existing athlete, training and performance access is tenant-scoped.
- Docker Compose now includes Redis and a worker; CI validates PostgreSQL migrations.

### Security

- Production rejects development credential/JWT secrets and synchronous job execution; XML entities, spoofed formats, unsafe paths and oversized uploads are blocked.
- Integration events and all object lookups are scoped to both tenant and athlete; nested audit secrets are redacted.

### Known limitations

- Garmin, TrainingPeaks and CORE are non-operational placeholders; no live provider synchronization is claimed.
- Generic import records are not yet mapped to training entities, and provider polling records await a live adapter.
- Local upload storage is single-host and has no malware scanner; production requires object storage and scanning.
- Personal tenants have no switching or invitation UI, and PostgreSQL row-level security is not enabled.
- Production requires PostgreSQL, Redis, a separately running worker, and operator-managed JWT/Fernet keys.
