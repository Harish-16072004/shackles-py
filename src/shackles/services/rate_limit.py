"""Rate limiting via slowapi.

The limiter is backed by Redis so limits are shared across web
instances. Applied per-route with the decorator:

    @router.post("/login")
    @limiter.limit("5/minute")
    async def login(request: Request, ...):
        ...
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from shackles.config import settings


# Global limiter. Routes opt in via decorators.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    default_limits=[],  # No global default — routes choose their own
    headers_enabled=True,
)


# ============================================================
# Common limit strings — reference these in routes
# ============================================================

LIMIT_LOGIN = "10/minute"
LIMIT_REGISTER = "5/hour"
LIMIT_PASSWORD_RESET = "5/hour"
LIMIT_CONTACT = "3/hour"
LIMIT_UPLOAD = "10/hour"
LIMIT_SCANNER = "120/minute"