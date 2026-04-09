"""
Remove tabelas de favoritos (obsoletas).

Revision ID: 004_remove_favorites
Revises: 003_remove_history
Create Date: 2026-02-02

MOTIVAÇÃO:
O sistema de favoritos foi removido da aplicação.
Os favoritos agora são gerenciados apenas no localStorage do navegador,
sem persistência no backend.

TABELAS REMOVIDAS:
- public.user_favorites
- public.favorite_location

ENDPOINTS REMOVIDOS:
- POST /api/v1/internal/eto/favorites/add
- GET /api/v1/internal/eto/favorites/list
- DELETE /api/v1/internal/eto/favorites/remove/{favorite_id}

"""

from alembic import op

# revision identifiers
revision = "004_remove_favorites"
down_revision = "003_remove_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove tabelas de favoritos."""

    print("\n" + "=" * 80)
    print("🧹 REMOVENDO TABELAS DE FAVORITOS (OBSOLETAS)")
    print("=" * 80)

    print("\n📝 Motivo: Sistema de favoritos movido para localStorage")
    print("📝 Não há mais persistência de favoritos no backend")

    # Drop índices primeiro (se existirem)
    print("\n🗑️  Removendo índices de favoritos...")
    op.execute(
        "DROP INDEX IF EXISTS idx_favorite_location_user_favorites CASCADE"
    )
    op.execute("DROP INDEX IF EXISTS idx_user_favorites_session CASCADE")
    op.execute("DROP INDEX IF EXISTS idx_user_favorites_user CASCADE")
    print("✅ Índices removidos")

    # Drop tabela favorite_location primeiro (tem FK para user_favorites)
    print("\n🗑️  Removendo tabela favorite_location...")
    op.execute("DROP TABLE IF EXISTS favorite_location CASCADE")
    print("✅ Tabela favorite_location removida")

    # Drop tabela user_favorites
    print("\n🗑️  Removendo tabela user_favorites...")
    op.execute("DROP TABLE IF EXISTS user_favorites CASCADE")
    print("✅ Tabela user_favorites removida")

    print("\n" + "=" * 80)
    print("✨ MIGRAÇÃO CONCLUÍDA")
    print("=" * 80)
    print("\nℹ️  Favoritos agora são gerenciados no localStorage do navegador")


def downgrade() -> None:
    """
    Recria tabelas de favoritos (para rollback se necessário).
    """
    print("\n⚠️  Recriando tabelas de favoritos...")

    # Recriar user_favorites
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_favorites (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL DEFAULT 'default',
            session_id VARCHAR(255),
            name VARCHAR(255) NOT NULL,
            lat DOUBLE PRECISION NOT NULL,
            lng DOUBLE PRECISION NOT NULL,
            cidade VARCHAR(255),
            estado VARCHAR(50),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_favorites_user "
        "ON user_favorites (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_favorites_session "
        "ON user_favorites (session_id)"
    )

    # Recriar favorite_location
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS favorite_location (
            id SERIAL PRIMARY KEY,
            user_favorites_id INTEGER REFERENCES user_favorites(id) ON DELETE CASCADE,
            location_id VARCHAR(255) NOT NULL,
            lat DOUBLE PRECISION NOT NULL,
            lng DOUBLE PRECISION NOT NULL,
            name VARCHAR(255),
            timezone VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_favorite_location_user_favorites "
        "ON favorite_location (user_favorites_id)"
    )

    print("✅ Tabelas de favoritos recriadas")
