# Security and privacy

JWTs authenticate users; active tenant memberships authorize data access. All athlete-owned queries include tenant scope and cross-tenant tests guard against IDOR. Passwords use bcrypt.

Provider credentials are JSON-encrypted with Fernet and prefixed with an envelope version. Keys come from environment configuration, are validated at startup, and development defaults are rejected in production. Rotation should decrypt with the old key and re-encrypt with a new version in a controlled job.

Uploads allow only FIT, TCX, GPX and CSV, enforce 25 MB by default, stream in bounded chunks, sanitize filenames, prevent path traversal and reject MIME/extension mismatches. XML entities are disabled. Raw tokens, credential ciphertext, storage keys and stack traces are excluded from client responses and structured logs.

Training, health and wellness data may be sensitive. Retention, export, account deletion, provider revocation and object deletion must be operated as one lifecycle. Production operators should apply least privilege, encrypted transport/storage, audit retention and incident response procedures.

## Threat assessment

- Stolen integration tokens: encrypted at rest, excluded from APIs/logs, revocable; production needs rotation and provider-side revocation monitoring.
- Malicious uploads: extension/MIME/signature allowlists, bounded streaming, sanitized generated paths and safe parsers; production must add malware scanning.
- Cross-tenant exposure: membership-derived tenant filters and IDOR tests; future defense-in-depth may add PostgreSQL RLS.
- Secret leakage: credentials are encrypted separately from non-secret configuration; secret-like configuration keys are rejected and nested audit details are recursively redacted.
- Duplicate delivery and replayed syncs: checksum uniqueness, idempotency keys and active-run control.
- Oversized files: client feedback plus server-enforced streaming limit.
- XML attacks: external entities and dangerous constructs are blocked by `defusedxml`.
- Log leakage: structured safe fields and generic client messages; operators must maintain redaction in downstream tooling.
