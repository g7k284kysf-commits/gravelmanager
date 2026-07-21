# Coding standards

Python targets 3.13, uses full type checking, Ruff formatting/linting, Pydantic boundary validation and SQLAlchemy 2 statements. Route handlers stay thin; domain behavior belongs in services or adapters. TypeScript is strict, components expose loading/error/empty states, and server contracts are typed in `lib/api.ts`.

Every change must preserve tenant scoping, UTC semantics, safe errors and secret redaction. New status transitions need tests. New providers require capability and failure tests. Migrations must upgrade and downgrade on PostgreSQL. Do not commit disabled tests, placeholder claims, unfinished markers or credentials in fixtures/logs.
