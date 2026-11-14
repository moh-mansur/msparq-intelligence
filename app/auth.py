"""
Shared-secret authentication for the prediction endpoints.

The predictions carry every pupil's name, marks, attendance and risk reading,
and until now anyone who knew a school's id could ask for them. Only the
school app calls this service, from its server, so a single secret shared
between the two is enough: the app sends it as a bearer token and every
prediction route checks it.

If INTELLIGENCE_API_KEY is not set the routes refuse every request rather than
falling back to open. A missing setting must never quietly publish pupil data.

/ and /health stay open: they reveal nothing, and the keep-awake job pings
/health without a key.
"""

import hmac
import logging
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


def _configured_key() -> str | None:
    # Read on each request so a key rotated in the host's settings applies
    # after a restart without a code change, and tests can set it freely.
    key = os.getenv("INTELLIGENCE_API_KEY", "").strip()
    return key or None


async def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    expected = _configured_key()

    if expected is None:
        logger.error("INTELLIGENCE_API_KEY is not set; refusing prediction request")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is not configured.",
        )

    provided = credentials.credentials if credentials else ""

    # compare_digest takes the same time whatever matches, so the key cannot
    # be guessed a character at a time from response timings.
    if not hmac.compare_digest(provided.encode(), expected.encode()):
        logger.warning("Rejected prediction request with a missing or wrong API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
