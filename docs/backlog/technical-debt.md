# Technical debt

- Goal hierarchies prevent direct self-parenting but do not yet detect longer cycles.
- Personal tenants have no switching UI, invitations or database row-level security.
- Local volume storage is single-host; production needs an S3-compatible adapter and scanning hook.
- Generic import records are not yet linked to authoritative training entities.
- Queue dead-letter handling, key-rotation tooling and retention orchestration need implementation.
