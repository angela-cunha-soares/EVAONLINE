"""
Remove climate_history schema (obsoleto).

Revision ID: 003_remove_history
Revises: 002_add_regional_coverage_postgis
Create Date: 2025-12-08

MOTIVAÇÃO:
Os dados históricos de referência agora são lidos diretamente dos arquivos
JSON em data/historical/cities/ via HistoricalDataLoader, que é mais rápido
e não requer queries SQL complexas.

NWS Stations agora usa API direta (find_nearest_active_station) sem precisar
do banco de dados.

TABELAS REMOVIDAS:
- climate_history.studied_cities
- climate_history.monthly_climate_normals
- climate_history.city_statistics
- climate_history.city_nearby_stations
- climate_history.weather_stations
- climate_history schema inteiro

MANTIDAS (essenciais):
- public.climate_data (dados multi-API)
- public.api_variables (metadados APIs)
- public.admin_users, user_cache, visitor_stats
- public.eto_results
"""

from alembic import op

# revision identifiers
revision = "003_remove_history"
down_revision = "002_regional_coverage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove schema climate_history e todas as suas tabelas."""

    print("\n" + "=" * 80)
    print("🧹 REMOVENDO SCHEMA CLIMATE_HISTORY (OBSOLETO)")
    print("=" * 80)

    print(
        "\n📝 Motivo: Dados históricos agora via JSON (HistoricalDataLoader)"
    )
    print("📝 NWS Stations agora via API direta (find_nearest_active_station)")

    # Drop schema cascade (remove todas as tabelas dentro)
    print("\n🗑️  Removendo schema climate_history...")
    op.execute("DROP SCHEMA IF EXISTS climate_history CASCADE")
    print("✅ Schema removido")

    print("\n" + "=" * 80)
    print("✨ MIGRAÇÃO CONCLUÍDA")
    print("=" * 80)
    print("\nℹ️  Dados históricos disponíveis em: data/historical/cities/")
    print(
        "ℹ️  Use: HistoricalDataLoader().get_reference_for_location(lat, lon)"
    )


def downgrade() -> None:
    """
    Não há downgrade - os dados históricos estão nos arquivos JSON.

    Se necessário restaurar o schema, use a migration 001 original.
    """
    print("\n⚠️  Downgrade não suportado")
    print("ℹ️  Os dados históricos estão em data/historical/cities/")
    print("ℹ️  Para restaurar schema, rode migration 001 manualmente")
