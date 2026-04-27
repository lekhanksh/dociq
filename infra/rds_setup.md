# Aurora PostgreSQL + pgvector

## Engine and Topology
- Aurora PostgreSQL (compatible with PG15+)
- Writer + at least one reader in production
- Private DB subnet group only
- Encryption at rest with CMK

## Mandatory Settings
- `Publicly accessible = false`
- `Deletion protection = true` (production)
- Backup retention:
  - Staging: 7 days
  - Production: 35 days + PITR
- Performance Insights enabled (prod)

## pgvector Setup
Run once per cluster database:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Stage 2 Table
Use `backend/sql/pgvector_stage2.sql` to create `rag_chunks` and indexes.

## Connectivity
- DB security group allows `5432` only from `dociq-app-sg`.
- Credentials and connection strings loaded from Secrets Manager.
