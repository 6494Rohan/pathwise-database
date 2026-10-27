# pathwise database

Schema and migrations for the pathwise PostgreSQL database, managed with **Alembic** (SQLAlchemy 2, psycopg 3). Extensions: **PostGIS** (jobs map: distances, map areas), **pgvector** (profile ↔ job matching), **pg_trgm** (typo-tolerant search).

The database itself (AWS RDS, dev) is created by Terraform in the **backend** repo (`backend/terraform`). This repo only changes what is inside it.

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env        # then set DATABASE_URL
```

### Which database

- **Local (free):** set `LOCAL_DB_PASSWORD` in `.env`, then `docker compose up -d` starts PostgreSQL 17 with PostGIS and pgvector. Point `DATABASE_URL` at it (local line in `.env.example`).
- **AWS RDS (dev):** build the URL from the backend repo:
  ```bash
  cd ../backend/terraform
  HOST=$(terraform output -raw db_host)
  PASSWORD=$(aws ssm get-parameter --with-decryption --name "$(terraform output -raw db_password_ssm_parameter)" --query Parameter.Value --output text)
  echo "DATABASE_URL=postgresql+psycopg://pathwise_admin:${PASSWORD}@${HOST}:5432/pathwise?sslmode=require"
  ```
  RDS only accepts your IP if it is in `allowed_cidrs` in `backend/terraform/terraform.tfvars`; when your IP changes, update it and run `terraform apply` there.

## Everyday commands

```bash
./.venv/bin/alembic upgrade head                      # apply all migrations
./.venv/bin/alembic downgrade -1                      # undo the last one
./.venv/bin/alembic current                           # where the database is
./.venv/bin/alembic history                           # all migrations
./.venv/bin/alembic upgrade head --sql                # print the SQL without a database
```

## Adding a change

1. Add or change models in `pathwise_db/` (import new model modules in `pathwise_db/models.py` so Alembic sees them).
2. `./.venv/bin/alembic revision --autogenerate -m "add jobs table"`
3. **Read the generated file** before applying: autogenerate misses some changes (renames, data moves, extension-specific indexes such as GiST/HNSW) and they must be written by hand.
4. `./.venv/bin/alembic upgrade head`, then commit the model change and the migration together.

## Conventions

- Migration files are named `YYYY_MM_DD_HHMM-<rev>_<slug>.py` so they sort by date.
- Constraint and index names follow `pathwise_db/base.py`'s naming convention, so migrations stay reviewable and reversible.
- Every migration has a working `downgrade()`.
- `migrations/env.py` ignores tables that belong to extensions (`spatial_ref_sys`, PostGIS `tiger`/`topology` schemas) so autogenerate never tries to drop them.
- Never commit `.env` or a password; the RDS password lives in SSM Parameter Store.
