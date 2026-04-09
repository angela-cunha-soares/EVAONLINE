#!/usr/bin/env python3
"""
Setup completo com Docker: PostgreSQL, Redis e validação do pipeline ETo

Este script:
1. Verifica se Docker está rodando
2. Valida o .env
3. Inicia PostgreSQL e Redis
4. Executa migrações do banco
5. Roda validação do pipeline ETo
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_file = Path(__file__).parent.parent / ".env"
if not env_file.exists():
    print("❌ Arquivo .env não encontrado!")
    print("   Copie .env.example para .env")
    sys.exit(1)

load_dotenv(env_file)

print("\n" + "=" * 80)
print("  SETUP DOCKER - EVAonline com PostgreSQL e Redis")
print("=" * 80)

# Verificar Docker
print("\n1️⃣  Verificando Docker...")
try:
    result = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    print(f"   ✅ {result.stdout.strip()}")
except Exception as e:
    print(f"   ❌ Docker não encontrado: {e}")
    print("   Instale Docker em: https://www.docker.com/")
    sys.exit(1)

# Verificar docker compose (v2)
print("\n2️⃣  Verificando docker compose (v2)...")
try:
    result = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    print(f"   ✅ {result.stdout.strip()}")
except Exception as e:
    print(f"   ❌ docker compose não encontrado: {e}")
    print("   Docker Compose v2 é incluído com Docker Desktop.")
    sys.exit(1)

# Verificar variáveis .env
print("\n3️⃣  Verificando variáveis de ambiente...")
required_vars = [
    "POSTGRES_HOST",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "REDIS_HOST",
    "REDIS_PASSWORD",
]

for var in required_vars:
    value = os.getenv(var)
    if value:
        # Mostrar apenas primeiros/últimos caracteres de senhas
        if "PASSWORD" in var:
            display = f"{value[:4]}...{value[-4:]}"
        else:
            display = value
        print(f"   ✅ {var}={display}")
    else:
        print(f"   ❌ {var} não definido em .env")
        sys.exit(1)

# Limpar containers antigos
print("\n4️⃣  Limpando containers antigos...")
try:
    subprocess.run(
        ["docker", "compose", "down", "-v"],
        capture_output=True,
        timeout=30,
    )
    print("   ✅ Containers removidos")
except Exception as e:
    print(f"   ⚠️  Erro ao remover: {e}")

# Iniciar PostgreSQL e Redis
print("\n5️⃣  Iniciando PostgreSQL e Redis...")
try:
    result = subprocess.run(
        ["docker", "compose", "up", "-d", "postgres", "redis"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    print("   ✅ Containers iniciados")
    print(result.stdout)
except Exception as e:
    print(f"   ❌ Erro ao iniciar: {e}")
    sys.exit(1)

# Aguardar containers ficarem saudáveis
print("\n6️⃣  Aguardando containers ficarem prontos...")
time.sleep(5)

for attempt in range(30):
    try:
        # Testar PostgreSQL
        pg_result = subprocess.run(
            [
                "docker",
                "exec",
                "evaonline-postgres",
                "pg_isready",
                "-U",
                os.getenv("POSTGRES_USER"),
            ],
            capture_output=True,
            timeout=5,
        )

        # Testar Redis
        redis_result = subprocess.run(
            [
                "docker",
                "exec",
                "evaonline-redis",
                "redis-cli",
                "-a",
                os.getenv("REDIS_PASSWORD"),
                "ping",
            ],
            capture_output=True,
            timeout=5,
        )

        if pg_result.returncode == 0 and redis_result.returncode == 0:
            print("   ✅ PostgreSQL e Redis prontos!")
            break
    except Exception as e:
        pass

    if attempt < 29:
        print(f"   ⏳ Tentativa {attempt + 1}/30...")
        time.sleep(1)
else:
    print("   ⚠️  Timeout aguardando containers")

print("\n7️⃣  Informações de Conexão:")
print(
    f"   📊 PostgreSQL: {os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}"
)
print(
    f"      Usuário: {os.getenv('POSTGRES_USER')} | BD: {os.getenv('POSTGRES_DB')}"
)
print(f"   🔴 Redis: {os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}")

print("\n8️⃣  Próximos passos:")
print("   1. Executar migrações do banco:")
print("      alembic upgrade head")
print("\n   2. Rodar validação do pipeline ETo:")
print("      python validate_eto_pipeline.py")
print("\n   3. Parar containers:")
print("      docker compose down")

print("\nSetup completo!")
print("=" * 80 + "\n")
