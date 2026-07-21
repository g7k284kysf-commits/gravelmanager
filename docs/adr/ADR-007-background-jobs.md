# ADR 007: Dramatiq background jobs

Status: accepted. Redis-backed Dramatiq handles imports and synchronization with bounded exponential retry. Durable state remains in PostgreSQL. A synchronous dispatcher keeps local tests deterministic and independent of Redis.
