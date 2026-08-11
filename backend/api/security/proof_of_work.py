"""
Stateless proof-of-work (anti-bot) challenge.

The client must find a `nonce` such that
    sha256(f"{challenge}:{nonce}")
has at least `difficulty_bits` leading zero bits. The challenge is derived
from a short time window + a subject (e.g. visitor_id), so no server-side
state is needed and solutions expire on their own.

Cost is asymmetric: a browser solves 16 bits in well under a second, but it
makes scripted mass-submission meaningfully more expensive.
"""

import hashlib
import time
from typing import Optional

from config.settings.app_config import get_settings

# Length of a challenge time window (seconds). Solutions are valid within the
# current or previous window to tolerate clock skew / slow solvers.
WINDOW_SECONDS = 300


def _window(ts: Optional[float] = None) -> int:
    return int((ts if ts is not None else time.time()) // WINDOW_SECONDS)


def make_challenge(subject: str, ts: Optional[float] = None) -> str:
    """Build the (stateless) challenge string for a subject."""
    settings = get_settings()
    salt = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).hexdigest()[:16]
    return f"{salt}:{_window(ts)}:{subject}"


def _leading_zero_bits(digest: bytes) -> int:
    bits = 0
    for byte in digest:
        if byte == 0:
            bits += 8
            continue
        # count leading zeros in this byte
        mask = 0x80
        while mask and not (byte & mask):
            bits += 1
            mask >>= 1
        break
    return bits


def verify_solution(
    subject: str,
    nonce: str,
    difficulty_bits: Optional[int] = None,
) -> bool:
    """
    Verify a PoW solution for `subject`.

    Accepts the current or previous time window. Returns True if the nonce
    satisfies the difficulty for either window's challenge.
    """
    if not nonce:
        return False
    if difficulty_bits is None:
        difficulty_bits = get_settings().POW_DIFFICULTY_BITS

    now = time.time()
    for ts in (now, now - WINDOW_SECONDS):
        challenge = make_challenge(subject, ts=ts)
        digest = hashlib.sha256(f"{challenge}:{nonce}".encode("utf-8")).digest()
        if _leading_zero_bits(digest) >= difficulty_bits:
            return True
    return False
