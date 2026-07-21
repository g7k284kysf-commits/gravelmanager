# Deployment guide

Copy `.env.example`, replace both security keys, and run `docker compose up --build`. The stack contains frontend, API, worker, PostgreSQL and Redis. The API applies migrations before serving; the worker consumes durable job messages. Seed only local/demo environments with `docker compose exec api python -m app.seed`.

For production use managed PostgreSQL/Redis/object storage, TLS at the edge, a generated Fernet key, a separate strong JWT secret, encrypted backups, restricted service identities and centralized redacted logs. Scale workers independently. Do not use the local upload volume across multiple hosts; implement the existing object-storage interface with S3-compatible storage first.

Health is `/health`. Readiness should additionally monitor migrations, database connectivity, Redis queue depth, failed sync/import counts and storage capacity.

Useful local commands:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed
docker compose exec worker dramatiq --version
curl -H "Authorization: Bearer $TOKEN" -F "file=@ride.gpx" http://localhost:8000/api/v1/imports/files
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/integrations/syncs
```
