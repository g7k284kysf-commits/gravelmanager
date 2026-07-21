# Integration platform

Providers implement metadata, capability declarations, connection tests and/or incremental polling. The registry currently exposes:

- Manual upload: available for FIT, TCX, GPX and CSV.
- Garmin, TrainingPeaks and CORE: clearly marked `coming_soon`; adapters contain no live calls.

Adding a provider requires an adapter, declared capabilities, normalized records, encrypted credential handling, cursor/idempotency behavior, safe errors, audit events, contract tests and UI copy that reflects actual availability.

Imports stream to object storage, calculate SHA-256, reject duplicates, parse defensively and persist source plus normalized payloads. Retries are bounded. Status transitions and counters are durable, while Redis only dispatches work. Correlation IDs connect user-facing history with redacted operational logs.

Normalized activity, wellness, planned-workout and generic import schemas provide provider-neutral extension points. Sprint 3 persists generic import records; linking them into training entities is a later, explicitly audited mapping step.

Race priorities connect integrations to planning semantics: A is the protected primary objective with a full peak/taper; B is a secondary performance objective with limited taper; C is a training race that normally remains part of training load without a taper.
