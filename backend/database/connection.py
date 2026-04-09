"""
Módulo base para configuração e conexão com o banco de dados PostgreSQL.
"""

import os
from contextlib import contextmanager
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações do PostgreSQL - usando variáveis de ambiente (obrigatórias)
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_USER = os.getenv("POSTGRES_USER", "evaonline")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")
PG_DB = os.getenv("POSTGRES_DB", "evaonline")

# Configurações de pool de conexão (produção-ready)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "30"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

# Validar variáveis críticas
if not PG_PASSWORD:
    msg = (
        "POSTGRES_PASSWORD environment variable is required. "
        "Set it in your .env file before running the application."
    )
    raise ValueError(msg)

# URL de conexão com o PostgreSQL (senha codificada para segurança)
# Usando psycopg3 (psycopg-binary) em vez de psycopg2
DATABASE_URL = (
    f"postgresql+psycopg://{quote_plus(PG_USER)}:{quote_plus(PG_PASSWORD)}"
    f"@{PG_HOST}:{PG_PORT}/{PG_DB}"
)

# Criar engine SQLAlchemy com configurações otimizadas para produção
engine = create_engine(
    DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_pre_ping=True,  # Verifica a conexão antes de usá-la
    echo=False,  # Define como True para ver logs SQL em desenvolvimento
    echo_pool=False,  # Não logar operações de pool por segurança
    connect_args={
        "connect_timeout": 5,  # Timeout de conexão: 5 segundos
        "options": "-c statement_timeout=10000",  # Query timeout: 10s
    },
)

# Criar fábrica de sessões
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos declarativos
Base = declarative_base()


@contextmanager
def get_db_context():
    """
    Context manager para sessões de banco de dados.
    Garante que a sessão seja fechada após o uso.

    Yields:
        Session: Uma sessão de banco de dados

    Exemplo:
        with get_db_context() as db:
            db.execute(...)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db():
    """
    FastAPI dependency para obter sessão de banco de dados.
    Garante que a sessão seja fechada após o uso.

    Yields:
        Session: Uma sessão de banco de dados

    Exemplo:
        @app.get("/")
        def read_root(db: Session = Depends(get_db)):
            return db.query(...).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
