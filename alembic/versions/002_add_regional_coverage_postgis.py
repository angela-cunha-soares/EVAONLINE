"""
Add regional coverage metadata table.

Revision ID: 002_regional_coverage
Revises: 001_climate_6apis
Create Date: 2025-11-15

Tabela de metadados de cobertura regional (sem dependência de PostGIS).
A detecção geográfica é feita em Python (Shapely + IBGE shapefile para
Brasil, bounding-boxes aritméticos para USA/Nordic).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "002_regional_coverage"
down_revision = "001_climate_6apis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Cria tabela regional_coverage com metadados por região.

    Estrutura:
    - region_id: Identificador único (nordic, brazil, usa, global)
    - region_name: Nome legível da região
    - bbox: Bounding box como JSONB {lat_min, lat_max, lon_min, lon_max}
    - sources: Array de fontes disponíveis na região
    - quality_tier: Nível de qualidade (high, medium, low)
    - resolution_km: Resolução típica em km
    - metadata: Dados adicionais (JSONB)
    """

    op.create_table(
        "regional_coverage",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column(
            "region_id",
            sa.String(50),
            nullable=False,
            unique=True,
            comment="Identificador único da região (nordic, brazil, usa, global)",
        ),
        sa.Column(
            "region_name",
            sa.String(100),
            nullable=False,
            comment="Nome legível da região",
        ),
        sa.Column(
            "bbox",
            postgresql.JSONB(),
            nullable=True,
            comment="Bounding box: {lat_min, lat_max, lon_min, lon_max}",
        ),
        sa.Column(
            "sources",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
            comment="Fontes de dados disponíveis",
        ),
        sa.Column(
            "quality_tier",
            sa.String(20),
            nullable=False,
            comment="Nível de qualidade: high, medium, low",
        ),
        sa.Column(
            "resolution_km",
            sa.Float(),
            nullable=True,
            comment="Resolução típica em quilômetros",
        ),
        sa.Column(
            "variables",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
            comment="Variáveis climáticas disponíveis",
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=True,
            comment="Metadados adicionais (modelos, atualizações, etc.)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_regional_coverage_region_id "
        "ON regional_coverage (region_id)"
    )

    _insert_regional_seeds()

    print("✅ Tabela regional_coverage criada")


def downgrade() -> None:
    """Remove tabela regional_coverage."""
    op.drop_index(
        "idx_regional_coverage_region_id", table_name="regional_coverage"
    )
    op.drop_table("regional_coverage")

    print("✅ Tabela regional_coverage removida")


def _insert_regional_seeds() -> None:
    """Insere seeds das regiões com bounding boxes."""

    conn = op.get_bind()

    regions = [
        {
            "region_id": "nordic",
            "region_name": "Nordic Region",
            "bbox": '{"lat_min": 54.0, "lat_max": 72.0, "lon_min": 4.0, "lon_max": 32.0}',
            "sources": "ARRAY['met_norway', 'open_meteo']",
            "quality_tier": "high",
            "resolution_km": 1.0,
            "variables": "ARRAY['air_temperature_max', 'air_temperature_min', 'relative_humidity_mean', 'precipitation_sum', 'wind_speed_mean']",
            "metadata": '{"model": "MEPS 2.5km + MET Nordic", "updates": "hourly", "post_processing": "radar + Netatmo crowdsourced"}',
        },
        {
            "region_id": "brazil",
            "region_name": "Brazil",
            "bbox": '{"lat_min": -34.0, "lat_max": 5.0, "lon_min": -74.0, "lon_max": -34.0}',
            "sources": "ARRAY['nasa_power', 'open_meteo', 'met_norway']",
            "quality_tier": "medium",
            "resolution_km": 11.0,
            "variables": "ARRAY['air_temperature_max', 'air_temperature_min', 'relative_humidity_mean']",
            "metadata": '{"model": "ECMWF IFS", "validation": "Xavier et al.", "note": "Use NASA POWER for historical precipitation"}',
        },
        {
            "region_id": "usa",
            "region_name": "United States",
            "bbox": '{"lat_min": 24.0, "lat_max": 50.0, "lon_min": -125.0, "lon_max": -66.0}',
            "sources": "ARRAY['nws_forecast', 'nws_stations', 'open_meteo', 'nasa_power']",
            "quality_tier": "high",
            "resolution_km": 2.5,
            "variables": "ARRAY['air_temperature_max', 'air_temperature_min', 'relative_humidity_mean', 'precipitation_sum', 'wind_speed_mean']",
            "metadata": '{"model": "NOAA HRRR + NBM", "updates": "hourly", "note": "NWS has highest quality for USA"}',
        },
        {
            "region_id": "global",
            "region_name": "Global (Rest of World)",
            "bbox": '{"lat_min": -90.0, "lat_max": 90.0, "lon_min": -180.0, "lon_max": 180.0}',
            "sources": "ARRAY['met_norway', 'open_meteo', 'nasa_power']",
            "quality_tier": "medium",
            "resolution_km": 9.0,
            "variables": "ARRAY['air_temperature_max', 'air_temperature_min', 'relative_humidity_mean']",
            "metadata": '{"model": "ECMWF IFS", "resolution": "9km", "note": "Lower precipitation quality - use Open-Meteo"}',
        },
    ]

    for r in regions:
        conn.execute(
            sa.text(
                f"""
                INSERT INTO regional_coverage (
                    region_id, region_name, bbox, sources, quality_tier,
                    resolution_km, variables, metadata
                ) VALUES (
                    :region_id, :region_name, CAST(:bbox AS jsonb),
                    {r['sources']}, :quality_tier, :resolution_km,
                    {r['variables']}, CAST(:metadata AS jsonb)
                )
            """
            ),
            {
                "region_id": r["region_id"],
                "region_name": r["region_name"],
                "bbox": r["bbox"],
                "quality_tier": r["quality_tier"],
                "resolution_km": r["resolution_km"],
                "metadata": r["metadata"],
            },
        )

    print(
        "✅ Seeds de cobertura regional inseridos (Nordic, Brazil, USA, Global)"
    )
