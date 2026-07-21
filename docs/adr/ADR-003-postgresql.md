# ADR 003: PostgreSQL authority

Status: accepted. PostgreSQL is authoritative for domain, job and audit state; JSON fields hold variable provider payloads. SQLite is a test adapter only. Redis and object storage are not sources of truth.
