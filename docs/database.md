# Database guide

PostgreSQL is the production database; SQLite remains a fast isolated test adapter. Alembic revision `0003` creates tenants, memberships, seasons, goals, competitions, connections, sync attempts, import files, import records and integration events. It also backfills every existing user into a personal tenant and scopes athlete, training and performance rows.

Tenant-aware composite indexes support principal list queries. Checksums are unique per tenant and athlete; sync idempotency keys are unique per tenant. Foreign keys use cascade only for true ownership and `SET NULL` where audit/history should survive a removed link.

Run `alembic upgrade head`. CI also runs `upgrade → downgrade 0002 → upgrade` against PostgreSQL. Back up PostgreSQL and upload objects together because import metadata references stored bytes.
