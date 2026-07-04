# Alembic Migrations

Database schema migrations for the HRMS backend.

- `env.py` — migration environment (loads config + model metadata).
- `script.py.mako` — template for generated migration scripts.
- `versions/` — generated migration files (one per schema change).

## Workflow (implementation phase)

```bash
# create a new migration from model changes
alembic revision --autogenerate -m "add employee tables"

# apply migrations
alembic upgrade head

# roll back one migration
alembic downgrade -1
```

## Rules

- Every schema change ships a **reviewed** migration — never auto-apply blindly.
- Migrations are ordered and immutable once merged; fix-forward with a new revision.
- Keep migrations in sync with `app.core.database.base.Base.metadata`.
