# ADR 006: Lightweight multi-tenancy

Status: accepted. Every athlete-owned row carries `tenant_id`; each user receives a personal tenant. Application queries enforce membership scope. Full organizations, billing and PostgreSQL RLS wait for validated workflows.
