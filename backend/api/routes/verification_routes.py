"""
Public email-verification endpoint.

This route is intentionally PUBLIC (not under /internal/) because the
confirmation link is clicked by the user in their browser. It only marks an
email as verified; it never triggers a calculation.
"""

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from loguru import logger

from backend.api.security.email_verification import confirm_token
from backend.api.security import pending_request

router = APIRouter(prefix="/verify", tags=["Verification"])


def _enqueue_pending(token: str, email: str) -> bool:
    """Enqueue the pending job (if any) tied to a just-confirmed token."""
    params = pending_request.consume(token)
    if not params:
        return False
    try:
        from backend.infrastructure.celery.tasks.eto_calculation import (
            calculate_eto_task,
        )

        calculate_eto_task.delay(**params)
        logger.info(f"📥 Pending historical job enqueued after confirm ({email})")
        # The task itself sends the "processing started" email (STEP 0) and
        # later the "results ready" email with the download link (STEP 6).
        return True
    except Exception as exc:
        logger.error(f"Failed to enqueue pending job: {exc}")
        return False


def _page(title: str, message: str, ok: bool) -> str:
    color = "#1D9E75" if ok else "#c0392b"
    icon = "✅" if ok else "⚠️"
    hint = (
        "You can close this tab and return to the EVAonline tab — the form "
        "will unlock automatically."
        if ok
        else "You can close this tab and try again on EVAonline."
    )
    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title></head>
<body style="font-family:system-ui,Segoe UI,Arial,sans-serif;background:#f5f7f8;
margin:0;padding:0;display:flex;min-height:100vh;align-items:center;justify-content:center">
<div style="background:#fff;border-radius:12px;padding:32px 28px;max-width:440px;
box-shadow:0 2px 16px rgba(0,0,0,.08);text-align:center">
<div style="font-size:42px">{icon}</div>
<h1 style="color:{color};font-size:20px;margin:12px 0 8px">{title}</h1>
<p style="color:#555;font-size:15px;line-height:1.5;margin:0 0 16px">{message}</p>
<p style="color:#888;font-size:13px;line-height:1.5;margin:0">{hint}</p>
</div></body></html>"""


@router.get("/email", response_class=HTMLResponse)
async def verify_email(token: str = Query(default="")) -> HTMLResponse:
    """Confirm an email-verification token clicked from the email link."""
    email = confirm_token(token)
    if email:
        enqueued = _enqueue_pending(token, email)
        if enqueued:
            msg = (
                "Your email is confirmed and your request is now in the "
                "processing queue. You'll get an email when it starts and "
                "another with the download link when it's ready."
            )
        else:
            msg = (
                "Your email is now verified (valid for 30 days). Return to the "
                "EVAonline tab and submit your Historical request — it will go "
                "straight to the processing queue."
            )
        return HTMLResponse(_page("Email confirmed", msg, ok=True))
    return HTMLResponse(
        _page(
            "Invalid or expired link",
            "This confirmation link is invalid or has expired. Please submit "
            "your request again to receive a new confirmation email.",
            ok=False,
        ),
        status_code=400,
    )
