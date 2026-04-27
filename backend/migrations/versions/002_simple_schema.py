"""Simple schema without extensions

Revision ID: 002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '002'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create companies table
    op.execute("""
        CREATE TABLE companies (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            plan VARCHAR(50) DEFAULT 'starter',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            is_active BOOLEAN DEFAULT TRUE
        )
    """)

    # Create users table
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
            email VARCHAR(255) NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            department VARCHAR(100) NOT NULL,
            role VARCHAR(50) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            is_active BOOLEAN DEFAULT TRUE,
            UNIQUE(company_id, email)
        )
    """)

    # Create documents table
    op.execute("""
        CREATE TABLE documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
            uploaded_by UUID REFERENCES users(id),
            filename VARCHAR(500) NOT NULL,
            department VARCHAR(100) NOT NULL,
            s3_key VARCHAR(1000) NOT NULL,
            file_size_bytes INTEGER,
            chunk_count INTEGER DEFAULT 0,
            status VARCHAR(50) DEFAULT 'processing',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Create document_chunks table
    op.execute("""
        CREATE TABLE document_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
            company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
            department VARCHAR(100) NOT NULL,
            chunk_text TEXT NOT NULL,
            page_number INTEGER,
            embedding TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Create query_logs table
    op.execute("""
        CREATE TABLE query_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID REFERENCES companies(id),
            user_id UUID REFERENCES users(id),
            department VARCHAR(100),
            question TEXT NOT NULL,
            chunks_used INTEGER,
            response_time_ms INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Create activity_logs table
    op.execute("""
        CREATE TABLE activity_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID REFERENCES companies(id),
            user_id UUID REFERENCES users(id),
            action VARCHAR(100) NOT NULL,
            document_id UUID REFERENCES documents(id),
            department VARCHAR(100),
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS activity_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS query_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS document_chunks CASCADE")
    op.execute("DROP TABLE IF EXISTS documents CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TABLE IF EXISTS companies CASCADE")
