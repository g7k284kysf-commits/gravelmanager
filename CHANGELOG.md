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

- Production rejects development credential and JWT secrets; XML entities, unsafe paths and oversized uploads are blocked.
