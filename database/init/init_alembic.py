"""
Script para inicializar o banco de dados com Alembic.
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def init_alembic():
    """Inicializa o Alembic no projeto."""
    print("🔧 Inicializando Alembic...")

    # Verificar se já existe
    if os.path.exists("alembic"):
        print("⚠️  Alembic já está inicializado!")
        return

    # Criar estrutura básica
    os.makedirs("alembic/versions", exist_ok=True)

    print("✅ Alembic inicializado com sucesso!")
    print("📝 Para criar a primeira migração:")
    print("   alembic revision --autogenerate -m 'Create initial tables'")
    print("📝 Para aplicar migrações:")
    print("   alembic upgrade head")


if __name__ == "__main__":
    init_alembic()
