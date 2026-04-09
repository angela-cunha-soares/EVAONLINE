import secrets
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import Boolean, Column, DateTime, Integer, String, text
from sqlalchemy.orm import validates

from backend.database.connection import Base


class AdminUser(Base):
    """
    Usuários administradores com validações de segurança.

    Roles:
    - SUPER_ADMIN: Acesso total
    - ADMIN: Grafana + Prometheus
    - DEVELOPER: Logs + Health check
    """

    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        String(50),
        default="DEVELOPER",
        nullable=False,
        # "SUPER_ADMIN", "ADMIN", "DEVELOPER"
    )
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    api_token = Column(String(255), default=lambda: secrets.token_urlsafe(32), unique=True)

    @validates("username")
    def validate_username(self, key, username):
        """Valida formato do username."""
        if not username or len(username.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not username.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers, " "underscores, and hyphens"
            )
        return username.strip().lower()

    @validates("email")
    def validate_email(self, key, email):
        """Valida formato do email."""
        if "@" not in email or "." not in email.split("@")[1]:
            raise ValueError("Invalid email format")
        return email.strip().lower()

    @validates("role")
    def validate_role(self, key, role):
        """Valida role permitido."""
        allowed_roles = ["SUPER_ADMIN", "ADMIN", "DEVELOPER"]
        if role not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return role

    def verify_password(self, password: str) -> bool:
        """Verifica senha usando bcrypt (seguro para produção)."""
        try:
            return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))
        except (ValueError, TypeError):
            # Se o hash estiver corrompido ou None, retorna False
            return False

    def set_password(self, password: str) -> None:
        """Define senha com hash bcrypt seguro (12 rounds)."""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Gera salt automaticamente e faz hash com 12 rounds (padrão seguro)
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        self.password_hash = hashed.decode("utf-8")

    def generate_api_token(self) -> str:
        """Gera novo token API seguro."""
        self.api_token = secrets.token_urlsafe(32)
        return self.api_token

    def __repr__(self):
        return f"<AdminUser({self.username}, role={self.role})>"
