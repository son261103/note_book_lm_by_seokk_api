"""Remove user authentication system

Revision ID: 34
Revises: 33

Changes:
1. Drop user_search_space_preferences table
2. Remove user_id foreign key from searchspaces table
3. Remove user_id foreign key from search_source_connectors table
4. Drop oauth_account table
5. Drop user table
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "34"
down_revision: str | None = "33"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Remove all user authentication related tables and foreign keys.
    """

    # Step 1: Drop user_search_space_preferences table
    op.execute(
        """
        DROP TABLE IF EXISTS user_search_space_preferences CASCADE;
        """
    )

    # Step 2: Remove user_id from searchspaces
    op.execute(
        """
        ALTER TABLE searchspaces DROP CONSTRAINT IF EXISTS searchspaces_user_id_fkey CASCADE;
        ALTER TABLE searchspaces DROP COLUMN IF EXISTS user_id CASCADE;
        """
    )

    # Step 3: Remove user_id from search_source_connectors
    op.execute(
        """
        ALTER TABLE search_source_connectors DROP CONSTRAINT IF EXISTS search_source_connectors_user_id_fkey CASCADE;
        ALTER TABLE search_source_connectors DROP COLUMN IF EXISTS user_id CASCADE;
        """
    )

    # Step 4: Drop the unique constraint that includes user_id
    op.execute(
        """
        ALTER TABLE search_source_connectors DROP CONSTRAINT IF EXISTS uq_searchspace_user_connector_type CASCADE;
        """
    )

    # Step 5: Create new unique constraint without user_id
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'uq_searchspace_connector_type'
            ) THEN
                ALTER TABLE search_source_connectors 
                ADD CONSTRAINT uq_searchspace_connector_type 
                UNIQUE (search_space_id, connector_type);
            END IF;
        END $$;
        """
    )

    # Step 6: Drop oauth_account table
    op.execute(
        """
        DROP TABLE IF EXISTS oauth_account CASCADE;
        """
    )

    # Step 7: Drop user table
    op.execute(
        """
        DROP TABLE IF EXISTS "user" CASCADE;
        """
    )


def downgrade() -> None:
    """
    Recreate user authentication system.
    Note: This will not restore data, only schema.
    """

    # Recreate user table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS "user" (
            id UUID PRIMARY KEY,
            email VARCHAR(320) NOT NULL,
            hashed_password VARCHAR(1024) NOT NULL,
            is_active BOOLEAN NOT NULL,
            is_superuser BOOLEAN NOT NULL,
            is_verified BOOLEAN NOT NULL,
            pages_limit INTEGER NOT NULL DEFAULT 500,
            pages_used INTEGER NOT NULL DEFAULT 0
        );
        
        CREATE UNIQUE INDEX IF NOT EXISTS ix_user_email ON "user" (email);
        """
    )

    # Recreate oauth_account table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_account (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            oauth_name VARCHAR(100) NOT NULL,
            access_token VARCHAR(1024) NOT NULL,
            expires_at INTEGER,
            refresh_token VARCHAR(1024),
            account_id VARCHAR(320) NOT NULL,
            account_email VARCHAR(320) NOT NULL
        );
        
        CREATE INDEX IF NOT EXISTS ix_oauth_account_oauth_name ON oauth_account (oauth_name);
        CREATE INDEX IF NOT EXISTS ix_oauth_account_account_id ON oauth_account (account_id);
        """
    )

    # Add user_id back to searchspaces
    op.execute(
        """
        ALTER TABLE searchspaces ADD COLUMN IF NOT EXISTS user_id UUID;
        ALTER TABLE searchspaces ADD CONSTRAINT searchspaces_user_id_fkey 
            FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;
        """
    )

    # Add user_id back to search_source_connectors
    op.execute(
        """
        ALTER TABLE search_source_connectors ADD COLUMN IF NOT EXISTS user_id UUID;
        ALTER TABLE search_source_connectors ADD CONSTRAINT search_source_connectors_user_id_fkey 
            FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;
        """
    )

    # Drop the new constraint and recreate the old one
    op.execute(
        """
        ALTER TABLE search_source_connectors DROP CONSTRAINT IF EXISTS uq_searchspace_connector_type;
        ALTER TABLE search_source_connectors ADD CONSTRAINT uq_searchspace_user_connector_type 
            UNIQUE (search_space_id, user_id, connector_type);
        """
    )

    # Recreate user_search_space_preferences table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_search_space_preferences (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            search_space_id INTEGER NOT NULL REFERENCES searchspaces(id) ON DELETE CASCADE,
            long_context_llm_id INTEGER REFERENCES llm_configs(id) ON DELETE SET NULL,
            fast_llm_id INTEGER REFERENCES llm_configs(id) ON DELETE SET NULL,
            strategic_llm_id INTEGER REFERENCES llm_configs(id) ON DELETE SET NULL,
            CONSTRAINT uq_user_searchspace UNIQUE (user_id, search_space_id)
        );
        
        CREATE INDEX IF NOT EXISTS ix_user_search_space_preferences_created_at 
            ON user_search_space_preferences (created_at);
        """
    )

