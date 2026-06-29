# Skill: add-migration

Generate and apply an Alembic database migration after a model change.

## Usage

```
add-migration "description of the schema change"
```

## Behavior

1. Check that the model change is already made in `src/terra/models/`
2. Generate the migration:
   ```bash
   uv run alembic revision --autogenerate -m "<description>"
   ```
3. Show the generated migration file contents — ask for confirmation before applying
4. Apply:
   ```bash
   uv run alembic upgrade head
   ```
5. Verify by checking `uv run alembic current`

## Notes

- Migration files land in `src/terra/db/migrations/versions/`
- Always review the generated migration — autogenerate can miss some changes (e.g. column type changes, custom constraints)
- In production (ECS), migrations run at container startup via `docker-entrypoint.sh` — the `serve` command calls `create_all` which is idempotent but not a substitute for proper migrations in production
