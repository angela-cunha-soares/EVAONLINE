# Alembic Migration: Regional Coverage Metadata

Migration que adiciona tabela de metadados de cobertura regional.

## 📋 Visão Geral

**Revision ID**: `002_regional_coverage`  
**Revises**: `001_climate_6apis`  
**Created**: 2025-11-15

Esta migration cria:

1. **Tabela `regional_coverage`**: Armazena bounding-boxes (JSONB) das regiões
2. **Seeds de regiões**: Nordic, Brazil, USA, Global
3. **Metadados**: Fontes disponíveis, quality tier, resolução

> **Nota**: A detecção geográfica de região é feita em Python (Shapely + IBGE shapefile para Brasil, bounding-boxes aritméticos para USA/Nordic). Esta tabela serve como referência de metadados.

## 🚀 Como Aplicar

### 1. Verificar Status Atual

```bash
# Ver migrations pendentes
alembic current
alembic heads

# Ver histórico
alembic history --verbose
```

### 2. Aplicar Migration

```bash
# Aplicar migration (upgrade)
alembic upgrade head

# Ou especificamente esta migration
alembic upgrade 002_regional_coverage
```

### 3. Verificar Aplicação

```bash
# Conectar ao PostgreSQL
docker exec -it evaonline-postgres psql -U evaonline -d evaonline

# Verificar tabela
\d regional_coverage

# Ver dados inseridos
SELECT region_id, region_name, quality_tier, resolution_km 
FROM regional_coverage;
```

## 📊 Estrutura da Tabela

```sql
CREATE TABLE regional_coverage (
    id SERIAL PRIMARY KEY,
    region_id VARCHAR(50) UNIQUE NOT NULL,          -- 'nordic', 'brazil', 'usa', 'global'
    region_name VARCHAR(100) NOT NULL,              -- Nome legível
    bbox JSONB NOT NULL,                            -- {"lat_min", "lat_max", "lon_min", "lon_max"}
    sources TEXT[] NOT NULL DEFAULT '{}',           -- Fontes disponíveis
    quality_tier VARCHAR(20) NOT NULL,              -- 'high', 'medium', 'low'
    resolution_km FLOAT,                            -- Resolução típica
    variables TEXT[] NOT NULL DEFAULT '{}',         -- Variáveis climáticas
    metadata JSONB,                                 -- Dados adicionais
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_regional_coverage_region_id 
    ON regional_coverage (region_id);
```

## 🗺️ Regiões Inseridas (Seeds)

| region_id | Bbox (lat_min, lat_max, lon_min, lon_max) | Quality | Resolution | Sources |
|-----------|-------------------------------------------|---------|------------|---------|
| `nordic`  | (54.0, 72.0, 4.0, 32.0)                  | high    | 1 km       | met_norway, open_meteo |
| `brazil`  | (-34.0, 5.0, -74.0, -34.0)               | medium  | 11 km      | nasa_power, open_meteo, met_norway |
| `usa`     | (24.0, 50.0, -125.0, -66.0)              | high    | 2.5 km     | nws_forecast, nws_stations, open_meteo |
| `global`  | (-90.0, 90.0, -180.0, 180.0)             | medium  | 9 km       | met_norway, open_meteo, nasa_power |

## 🐍 Detecção de Região (Python)

A detecção geográfica é feita inteiramente em Python, sem dependência de banco:

```python
from backend.core.utils.geo_utils import GeographicUtils

region = GeographicUtils.detect_geographic_region(lat=-22.7, lon=-47.6)
# Retorna: "brasil" (usa IBGE shapefile para detecção precisa)
```

## 🔄 Rollback

```bash
alembic downgrade 001_climate_6apis
```

---

**Migration**: `alembic/versions/002_add_regional_coverage_postgis.py`
