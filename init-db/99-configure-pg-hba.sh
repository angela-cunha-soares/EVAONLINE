#!/bin/bash
set -e
# Script para configurar pg_hba.conf durante inicialização do PostgreSQL.
# Executado automaticamente pelo Docker entrypoint (init-db/ convention).

echo "Configurando pg_hba.conf..."

# Remove a regra genérica que requer senha para tudo
sed -i '/^host all all all scram-sha-256/d' "$PGDATA/pg_hba.conf"

# Adiciona configurações extras ao pg_hba.conf
if [ -f /tmp/pg_hba_extra.conf ]; then
    cat /tmp/pg_hba_extra.conf >> "$PGDATA/pg_hba.conf"
    echo "Configurações aplicadas com sucesso!"
else
    echo "Arquivo /tmp/pg_hba_extra.conf não encontrado!"
fi

# Recarrega a configuração do PostgreSQL
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT pg_reload_conf();" || true
