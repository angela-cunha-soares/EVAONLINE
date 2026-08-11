"""
Public result-download endpoint.

Serves historical result files via an unguessable token. This route is PUBLIC
(not under /internal/) because the link is opened directly by the user from
the results email. Expired/invalid tokens return 410/404.
"""

import mimetypes

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, HTMLResponse

from backend.infrastructure.storage import result_files

router = APIRouter(prefix="/download", tags=["Download"])


def _expired_page() -> str:
    return """<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Link expired</title></head>
<body style="font-family:system-ui,Segoe UI,Arial,sans-serif;background:#f5f7f8;
margin:0;display:flex;min-height:100vh;align-items:center;justify-content:center">
<div style="background:#fff;border-radius:12px;padding:32px 28px;max-width:460px;
box-shadow:0 2px 16px rgba(0,0,0,.08);text-align:center">
<div style="font-size:42px">⏳</div>
<h1 style="color:#c0392b;font-size:20px;margin:12px 0 8px">Link expired or invalid</h1>
<p style="color:#555;font-size:15px;line-height:1.5;margin:0">
This download link is no longer available. Result files are kept for a limited
time (48 hours) and then removed. Please submit your request again on EVAonline
to generate a new file.</p></div></body></html>"""


@router.get("/{token}")
async def download_result(token: str):
    """Download a result file by token (if still available)."""
    meta = result_files.resolve(token)
    if not meta:
        return HTMLResponse(_expired_page(), status_code=410)

    filename = meta.get("filename", "result")
    media_type = (
        mimetypes.guess_type(filename)[0] or "application/octet-stream"
    )
    return FileResponse(
        meta["path"],
        media_type=media_type,
        filename=filename,
    )


# Optional token via query string (?token=...) for convenience/compat.
@router.get("")
async def download_result_query(token: str = Query(default="")):
    return await download_result(token)
