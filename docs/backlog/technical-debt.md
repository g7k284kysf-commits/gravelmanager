# Technical debt

- Personal tenants have no switching UI, invitations or database row-level security.
- Local volume storage is single-host; production needs an S3-compatible adapter and scanning hook.
- Generic import records are not yet linked to authoritative training entities.
- Provider synchronization persists lifecycle metadata and counters, but normalized provider records await the first live adapter and import-to-training mapping.
- Queue dead-letter handling, key-rotation tooling and retention orchestration need implementation.
