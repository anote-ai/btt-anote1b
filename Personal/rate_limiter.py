"""
Rate limiting middleware for API endpoints

Protects against abuse and ensures fair usage of the leaderboard API.
"""
import os

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

_RL_OFF = os.getenv("DISABLE_RATE_LIMIT", "").lower() in ("1", "true", "yes")

# Rate limit configurations for different endpoint types
RATE_LIMITS = {
    "default": "1000000/minute" if _RL_OFF else "100/minute",
    "submission": "1000000/minute" if _RL_OFF else "10/minute",
    "admin": "1000000/minute" if _RL_OFF else "5/minute",
    "leaderboard": "1000000/minute" if _RL_OFF else "200/minute",
}


def setup_rate_limiting(app):
    """
    Configure rate limiting for the FastAPI app
    
    Usage in main.py:
        from rate_limiter import setup_rate_limiting
        setup_rate_limiting(app)
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    return limiter

