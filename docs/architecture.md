# Architecture

Gravel Manager 0.3.0 is a modular monolith: Next.js renders the product UI; FastAPI owns authenticated REST contracts and domain orchestration; PostgreSQL is authoritative; Redis/Dramatiq executes imports and future provider synchronization outside requests. This keeps operations simple while preserving seams for later services.

## Boundaries

- `api/routes` validates HTTP input and resolves the current user and tenant.
- `services` owns use cases, transactions, synchronization state and audit events.
- `integrations` owns provider contracts, credential envelopes, parsers and object storage.
- `domain` contains provider-neutral normalized records.
- `models` and `repositories` own persistence.

Every athlete-owned row carries `tenant_id`; routes derive it from an active membership and include it in every query. Sprint 3 creates a personal tenant per user. Organization switching and delegated coaching are deliberate future extensions.

Imports follow `upload → queued → processing → succeeded/failed`. Bytes live behind an object-storage interface; metadata and normalized records live in PostgreSQL. Sync requests use tenant-scoped idempotency keys and persist counters, cursors, correlation IDs and safe errors. Provider adapters declare capabilities so unsupported operations fail explicitly.

## Runtime and trust boundaries

The browser never receives encrypted credentials. FastAPI encrypts credential JSON using Fernet before persistence. Production startup rejects development keys. File size, extension, media type, storage path and duplicate checksum are validated; XML parsing disables external entities. Logs and API errors exclude tokens and raw exceptions.

The API and worker share the database and upload volume. Redis is disposable coordination infrastructure; PostgreSQL remains the source of truth. UTC is used for instants and athlete planning uses calendar dates. See the ADRs for individual decisions.
