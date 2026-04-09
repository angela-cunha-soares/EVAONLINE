"""
Utilitários para validação e envio de emails.

Este módulo fornece funções para:
- Validação de formato de email
- Envio de emails via SMTP (Gmail/SendGrid/AWS SES)
- Suporte a anexos (CSV, Excel) para modo HISTORICAL_EMAIL

Configuração via variáveis de ambiente:
- EMAIL_BACKEND: "smtp" (padrão), "sendgrid", "aws_ses"
- SMTP_HOST: Servidor SMTP (ex: smtp.gmail.com)
- SMTP_PORT: Porta SMTP (587 para TLS, 465 para SSL)
- SMTP_USER: Usuário SMTP
- SMTP_PASSWORD: Senha ou App Password
- SMTP_FROM: Email remetente padrão
- SMTP_USE_TLS: "true" ou "false" (padrão: true)
"""

import os
import re
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

# Carregar variáveis de ambiente do .env
load_dotenv()

# Configurações via env vars com fallbacks seguros
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "smtp")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

# Resend API (alternative to SMTP — works on DigitalOcean)
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "onboarding@resend.dev")


def validate_email(email: str) -> bool:
    """
    Valida formato do email.

    Args:
        email: Endereço de email a validar

    Returns:
        True se email válido, False caso contrário

    Example:
        >>> validate_email("user@example.com")
        True
        >>> validate_email("invalid.email")
        False
    """
    if not email or not isinstance(email, str):
        return False

    # Padrão RFC 5322 simplificado
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def send_email(
    to: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None,
) -> bool:
    """
    Envia email simples (texto) via SMTP.

    Usa configurações de SMTP do ambiente (SMTP_HOST, SMTP_USER, etc).
    Suporta Gmail (com App Password), SendGrid, AWS SES e outros.

    Args:
        to: Email destinatário
        subject: Assunto do email
        body: Corpo do email (texto simples)
        from_email: Email remetente (opcional, usa SMTP_FROM do env)

    Returns:
        True se enviado com sucesso, False caso contrário

    Example:
        >>> # Requer variáveis de ambiente configuradas
        >>> success = send_email(
        ...     to="user@example.com",
        ...     subject="Teste",
        ...     body="Mensagem de teste"
        ... )
    """
    if not validate_email(to):
        logger.error(f"Email inválido: {to}")
        return False

    # Verificar configurações SMTP
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning(
            "SMTP não configurado (SMTP_USER/SMTP_PASSWORD ausentes). "
            "Email simulado."
        )
        logger.info(
            f"[EMAIL SIMULADO] Para: {to}, Assunto: {subject}, "
            f"Corpo: {body[:50]}..."
        )
        return True

    sender = from_email or SMTP_FROM

    try:
        # Criar mensagem
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Conectar e enviar
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email enviado com sucesso para {to}: {subject}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Falha autenticação SMTP: {e}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"Erro SMTP ao enviar email: {e}")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao enviar email: {e}", exc_info=True)
        return False


def send_email_with_attachment(
    to: str,
    subject: str,
    body: str,
    attachment_path: str,
    from_email: Optional[str] = None,
) -> bool:
    """
    Envia email com anexo (CSV, Excel) via SMTP.

    Usado no modo HISTORICAL_EMAIL para enviar dados processados
    ao usuário após task Celery concluir processamento em background.

    Args:
        to: Email destinatário
        subject: Assunto do email
        body: Corpo do email (texto simples)
        attachment_path: Caminho completo do arquivo anexo (.csv, .xlsx)
        from_email: Email remetente (opcional, usa SMTP_FROM do env)

    Returns:
        True se enviado com sucesso, False caso contrário

    Raises:
        FileNotFoundError: Se arquivo anexo não existir

    Example:
        >>> # Após processar dados históricos
        >>> success = send_email_with_attachment(
        ...     to="user@example.com",
        ...     subject="EVAonline: Dados prontos!",
        ...     body="Seus dados estão anexados",
        ...     attachment_path="/tmp/dados.xlsx"
        ... )
    """
    if not validate_email(to):
        logger.error(f"Email inválido: {to}")
        return False

    # Verificar se arquivo existe
    file_path = Path(attachment_path)
    if not file_path.exists():
        logger.error(f"Arquivo anexo não encontrado: {attachment_path}")
        raise FileNotFoundError(f"Anexo não encontrado: {attachment_path}")

    # Verificar configurações SMTP
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning(
            "SMTP não configurado (SMTP_USER/SMTP_PASSWORD ausentes). "
            "Email simulado."
        )
        logger.info(
            f"[EMAIL SIMULADO COM ANEXO] Para: {to}, "
            f"Assunto: {subject}, Anexo: {attachment_path}"
        )
        return True

    sender = from_email or SMTP_FROM

    try:
        # Criar mensagem
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Anexar arquivo
        with open(attachment_path, "rb") as f:
            attachment = MIMEApplication(f.read())
            attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=file_path.name,
            )
            msg.attach(attachment)

        # Conectar e enviar
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(
            f"Email com anexo enviado com sucesso para {to}: "
            f"{subject} (anexo: {file_path.name})"
        )
        return True

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Falha autenticação SMTP: {e}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"Erro SMTP ao enviar email: {e}")
        return False
    except Exception as e:
        logger.error(
            f"Erro inesperado ao enviar email com anexo: {e}",
            exc_info=True,
        )
        return False


# ============================================================================
# RESEND API FUNCTIONS (HTTPS - bypasses SMTP port blocking)
# ============================================================================

def _send_via_resend(
    to: str,
    subject: str,
    html_body: str,
    attachment_path: Optional[str] = None,
    from_email: Optional[str] = None,
) -> bool:
    """
    Envia email via Resend API (HTTPS).

    Usa API REST do Resend, que não precisa de porta SMTP.
    Funciona em qualquer servidor, incluindo DigitalOcean.
    """
    import resend
    from backend.infrastructure.cache.api_usage_tracker import (
        check_api_quota,
        track_api_call,
    )

    # Check Resend daily quota (100/day free tier)
    if not check_api_quota("resend"):
        logger.error("🚫 Resend daily email quota exceeded (100/day)")
        return False

    resend.api_key = RESEND_API_KEY
    sender = from_email or RESEND_FROM

    try:
        params: dict = {
            "from": sender,
            "to": [to],
            "subject": subject,
            "html": html_body,
        }

        # Adicionar anexo se fornecido
        if attachment_path:
            file_path = Path(attachment_path)
            if not file_path.exists():
                logger.error(f"Arquivo anexo não encontrado: {attachment_path}")
                raise FileNotFoundError(f"Anexo não encontrado: {attachment_path}")

            with open(attachment_path, "rb") as f:
                file_content = f.read()

            params["attachments"] = [
                {
                    "filename": file_path.name,
                    "content": list(file_content),
                }
            ]

        email_response = resend.Emails.send(params)
        track_api_call("resend")
        logger.info(
            f"📧 Email enviado via Resend para {to}: {subject} "
            f"(id: {email_response.get('id', 'N/A')})"
        )
        return True

    except Exception as e:
        logger.error(f"❌ Erro ao enviar email via Resend: {e}", exc_info=True)
        return False


# ============================================================================
# SMTP FALLBACK FUNCTIONS
# ============================================================================

def _send_via_smtp(
    to: str,
    subject: str,
    html_body: str,
    attachment_path: Optional[str] = None,
    from_email: Optional[str] = None,
) -> bool:
    """Envia email via SMTP (fallback se Resend não configurado)."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP não configurado. Email simulado.")
        logger.info(f"[EMAIL SIMULADO] Para: {to}, Assunto: {subject}")
        return True

    sender = from_email or SMTP_FROM

    try:
        if attachment_path:
            file_path = Path(attachment_path)
            msg = MIMEMultipart("mixed")
            msg["From"] = sender
            msg["To"] = to
            msg["Subject"] = subject

            html_part = MIMEMultipart("alternative")
            html_part.attach(MIMEText(html_body, "html", "utf-8"))
            msg.attach(html_part)

            with open(attachment_path, "rb") as f:
                attachment = MIMEApplication(f.read())
                attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=file_path.name,
                )
                msg.attach(attachment)
        else:
            msg = MIMEMultipart("alternative")
            msg["From"] = sender
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"📧 Email enviado via SMTP para {to}: {subject}")
        return True

    except Exception as e:
        logger.error(f"❌ Erro ao enviar email via SMTP: {e}", exc_info=True)
        return False


# ============================================================================
# PUBLIC API (auto-selects Resend or SMTP)
# ============================================================================

def send_html_email(
    to: str,
    subject: str,
    html_body: str,
    from_email: Optional[str] = None,
) -> bool:
    """
    Envia email HTML (sem anexo).

    Usa Resend API se RESEND_API_KEY configurado, senão SMTP.
    """
    if not validate_email(to):
        logger.error(f"Email inválido: {to}")
        return False

    if RESEND_API_KEY:
        return _send_via_resend(to, subject, html_body, from_email=from_email)
    return _send_via_smtp(to, subject, html_body, from_email=from_email)


def send_html_email_with_attachment(
    to: str,
    subject: str,
    html_body: str,
    attachment_path: str,
    from_email: Optional[str] = None,
) -> bool:
    """
    Envia email HTML com anexo.

    Usa Resend API se RESEND_API_KEY configurado, senão SMTP.
    """
    if not validate_email(to):
        logger.error(f"Email inválido: {to}")
        return False

    file_path = Path(attachment_path)
    if not file_path.exists():
        logger.error(f"Arquivo anexo não encontrado: {attachment_path}")
        raise FileNotFoundError(f"Anexo não encontrado: {attachment_path}")

    if RESEND_API_KEY:
        return _send_via_resend(to, subject, html_body, attachment_path, from_email=from_email)
    return _send_via_smtp(to, subject, html_body, attachment_path, from_email=from_email)
