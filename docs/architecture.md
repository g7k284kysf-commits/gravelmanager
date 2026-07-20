# Architecture

Gravel Manager is a two-service monorepo backed by PostgreSQL. The Next.js App Router client owns presentation and browser session storage. FastAPI owns validation, authentication, authorization, training-load calculations, and persistence.

Requests enter through versioned `/api/v1` routes. JWT subjects resolve to database users before protected handlers execute, and every athlete or training query is scoped by that user identifier. SQLAlchemy models remain persistence-focused; Pydantic schemas define API contracts; service modules contain domain calculations.

## Training load

The dashboard derives Chronic Training Load (CTL) from a 42-day exponential response and Acute Training Load (ATL) from a 7-day response. Training Stress Balance (TSB) is `CTL - ATL`. Missing TSS values contribute zero rather than being estimated.

## Security

- Passwords are hashed with bcrypt using a work factor of 12.
- Access tokens are signed JWTs with explicit type, issued-at, expiry, and subject claims.
- Protected resources are always filtered by the authenticated user.
- Secrets enter containers through environment variables and are never committed.

