"""
Lightweight anti-bot / anti-abuse middleware.

This is a first line of defence, not a silver bullet — real bot defence
also relies on: email OTP at signup, the math-captcha on sensitive forms,
server-side minimum-watch-time checks in views.watch_ad, and the
one-view-per-user-per-campaign unique constraint on AdView.
"""
import time

from django.core.cache import cache
from django.http import HttpResponse

# requests allowed per IP per WINDOW_SECONDS before a temporary soft-block
MAX_REQUESTS = 120
WINDOW_SECONDS = 60


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith("/static/") or path in ("/favicon.ico", "/service-worker.js", "/sw.js"):
            return self.get_response(request)

        ip = _client_ip(request)
        key = f"ratelimit:{ip}:{int(time.time() // WINDOW_SECONDS)}"
        count = cache.get(key, 0) + 1
        cache.set(key, count, timeout=WINDOW_SECONDS)

        if count > MAX_REQUESTS:
            return HttpResponse(
                "Too many requests — please slow down. (Automated traffic protection)",
                status=429,
            )

        request.client_ip = ip
        return self.get_response(request)
