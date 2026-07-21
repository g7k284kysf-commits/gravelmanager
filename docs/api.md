# API guide

Swagger is available at `/docs` and OpenAPI JSON at `/openapi.json`. Product endpoints are under `/api/v1`; all except registration, login and health require a bearer JWT.

Planning resources are `/seasons`, `/goals` and `/competitions`. Integration resources are `/integrations/providers`, `/integrations/connections`, `/integrations/syncs` and `/integrations/events`. File ingestion uses `/imports/files`, `/imports/files/{id}/process` and `/imports/files/{id}/records`.

List endpoints use `offset` and `limit`. Cross-tenant IDs return 404. Duplicate uploads return 409 with the existing import ID. Validation errors return 422. Credentials and storage keys are never response fields. Provider capability errors are explicit and do not imply a live connection.
