"""Bearer-token guard for the management API.

Device config downloads stay public (phones can't send headers); everything
that reads or changes inventory — including SIP secrets — requires the token.
"""

import hmac
import os

from fastapi import Header, HTTPException

from ..config import get_config


def expected_api_token() -> str:
    return os.environ.get("PROVISIONER_API_TOKEN") or get_config().server.api_token


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    expected = expected_api_token()
    if not expected:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API token")
    if not hmac.compare_digest(authorization.removeprefix("Bearer "), expected):
        raise HTTPException(status_code=401, detail="Invalid API token")
