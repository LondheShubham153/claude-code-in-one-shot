from fastapi import Request
from slowapi import Limiter


def get_real_ip(request: Request) -> str:
    """Resolve client IP, honoring X-Forwarded-For from the nginx in front.

    Backend is `expose:`d only (not `ports:`), so the only path to it is via
    nginx — XFF spoofing requires getting onto the docker network first.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # First IP is the original client; the rest are intermediate proxies.
        return xff.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


limiter = Limiter(key_func=get_real_ip, default_limits=[])
