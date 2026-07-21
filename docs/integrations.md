# Integration platform

Providers implement metadata, capability declarations, connection tests and/or incremental polling. The registry currently exposes:

- Manual upload: operational for FIT, TCX, GPX and CSV ingestion; it does not expose polling sync.
- Garmin, TrainingPeaks and CORE: clearly marked non-operational `coming_soon`; adapters contain no live calls and their test/sync controls remain disabled.

Adding a provider requires an adapter, declared capabilities, normalized records, encrypted credential handling, cursor/idempotency behavior, safe errors, audit events, contract tests and UI copy that reflects actual availability.

Imports stream to storage, validate extension, MIME type and format signature, calculate SHA-256, reject duplicates, parse defensively and persist source plus normalized payloads. The development adapter stores files below `/tmp/gravel-manager-uploads` by default; Docker mounts `/data/uploads`. Production must replace this single-host adapter and add malware scanning. Retries are bounded. Status transitions and counters are durable, while Redis only dispatches work. Correlation IDs connect user-facing history with recursively redacted operational logs.

Normalized activity, wellness, planned-workout and generic import schemas provide provider-neutral extension points. Sprint 3 persists generic manual-import records. Provider sync lifecycle and counters are durable and concurrency-safe, but persisting normalized polling results and linking either source into training entities is a later, explicitly audited mapping step.

Race priorities connect integrations to planning semantics: A is the protected primary objective with a full peak/taper; B is a secondary performance objective with limited taper; C is a training race that normally remains part of training load without a taper.
