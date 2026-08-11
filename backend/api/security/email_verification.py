"""
One-time email verification for the historical mode.

Rationale: historical requests deliver results (and progress notifications)
to an arbitrary email address supplied by the user. Without verification,
anyone can (a) enter a victim's address to spam their inbox (email-bombing)
and (b) evade per-email rate limits by cycling addresses. Requiring the user
to confirm ownership once closes both vectors.

Flow (verify-then-submit):
  1. Historical request with an unverified email -> a confirmation link is
     emailed; the calculation is NOT dispatched.
  2. User clicks the link -> email marked verified in Redis (long TTL).
  3. User resubmits -> request proceeds.

State is kept in Redis:
  - email_verified:<email>        (verified flag, long TTL)
  - email_verify_token:<token>    (token -> email, short TTL)
  - email_verify_sent:<email>     (cooldown to avoid resending, short TTL)
"""

import secrets
from typing import Optional

from loguru import logger
from redis import Redis

from config.settings.app_config import get_settings

VERIFIED_TTL = 86400 * 30         # 30 days
TOKEN_TTL = 1800                  # 30 minutes
SEND_COOLDOWN = 300               # 5 minutes between verification emails


def _redis() -> Redis:
    return Redis.from_url(get_settings().redis.redis_url, decode_responses=True)


def _norm(email: str) -> str:
    return (email or "").strip().lower()


def is_verified(email: str) -> bool:
    """True if the email has already confirmed ownership."""
    try:
        return bool(_redis().get(f"email_verified:{_norm(email)}"))
    except Exception as exc:
        logger.error(f"is_verified error: {exc}")
        # Fail closed: treat as unverified so we don't dispatch on Redis errors.
        return False


def _build_message(link: str, lang: str) -> tuple[str, str]:
    footer_pt = (
        "\n\n---\n"
        "EVAonline — Web-based global reference EVApotranspiration estimate\n"
        "Método FAO-56 Penman-Monteith | Este é um e-mail automático.\n"
        "© 2024-2026 EVAonline | https://github.com/angela-cunha-soares/EVAONLINE"
    )
    footer_en = (
        "\n\n---\n"
        "EVAonline — Web-based global reference EVApotranspiration estimate\n"
        "FAO-56 Penman-Monteith method | This is an automated email.\n"
        "© 2024-2026 EVAonline | https://github.com/angela-cunha-soares/EVAONLINE"
    )
    if (lang or "en").lower().startswith("pt"):
        subject = "EVAonline — Confirme seu e-mail"
        body = (
            "Olá,\n\n"
            "Recebemos uma solicitação de cálculo no modo Histórico do "
            "EVAonline usando este e-mail. Para confirmar que o endereço é "
            "seu e receber os resultados, clique no link abaixo:\n\n"
            f"{link}\n\n"
            "O link expira em 30 minutos. Após a confirmação, o e-mail "
            "permanece válido por 30 dias; depois desse período será "
            "necessário confirmá-lo novamente. Se você não fez essa "
            "solicitação, ignore este e-mail." + footer_pt
        )
    else:
        subject = "EVAonline — Confirm your email"
        body = (
            "Hello,\n\n"
            "We received a Historical-mode calculation request on EVAonline "
            "using this email. To confirm the address is yours and receive "
            "the results, click the link below:\n\n"
            f"{link}\n\n"
            "The link expires in 30 minutes. Once confirmed, the email stays "
            "valid for 30 days; after that you will need to confirm it again. "
            "If you did not make this request, please ignore this email."
            + footer_en
        )
    return subject, body


def send_verification(
    email: str,
    lang: str = "en",
    pending: Optional[dict] = None,
) -> bool:
    """
    Create a token and email a confirmation link. Rate-limited per email.

    Args:
        email: recipient
        lang: 'pt' or 'en'
        pending: optional resolved Celery task kwargs to enqueue when the user
            clicks the link (hybrid flow). Stored under the same token.

    Returns True if an email was sent (or already recently sent).
    """
    from backend.core.utils.email_utils import send_email
    from backend.api.security import pending_request

    norm = _norm(email)
    try:
        redis = _redis()
        # Cooldown: avoid resending on every retry/refresh. Bypassed when a
        # pending request is attached (each job needs its own confirmation;
        # volume is capped by the per-email daily limit).
        cooldown_key = f"email_verify_sent:{norm}"
        if pending is None and redis.get(cooldown_key):
            logger.info(f"Verification email already sent recently to {norm}")
            return True

        token = secrets.token_urlsafe(32)
        redis.set(f"email_verify_token:{token}", norm, ex=TOKEN_TTL)
        redis.set(cooldown_key, "1", ex=SEND_COOLDOWN)
        if pending is not None:
            pending_request.save(token, pending, ttl=TOKEN_TTL)

        base = get_settings().PUBLIC_BASE_URL.rstrip("/")
        link = f"{base}/api/v1/verify/email?token={token}"
        subject, body = _build_message(link, lang)
        ok = send_email(norm, subject, body)
        if not ok:
            logger.error(f"Failed to send verification email to {norm}")
        return ok
    except Exception as exc:
        logger.error(f"send_verification error: {exc}")
        return False


def confirm_token(token: str) -> Optional[str]:
    """
    Confirm a token: mark its email as verified and consume the token.
    Returns the verified email, or None if the token is invalid/expired.
    """
    if not token:
        return None
    try:
        redis = _redis()
        tkey = f"email_verify_token:{token}"
        email = redis.get(tkey)
        if not email:
            return None
        redis.set(f"email_verified:{email}", "1", ex=VERIFIED_TTL)
        redis.delete(tkey)
        logger.info(f"✅ Email verified: {email}")
        return email
    except Exception as exc:
        logger.error(f"confirm_token error: {exc}")
        return None
