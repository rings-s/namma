"""Throttles for the authentication endpoints.

Login is the one anonymous endpoint where abuse is targeted, so it gets a
dedicated, tight rate limit keyed on *both* the client IP and the email being
tried. That way a single IP spraying many accounts and a distributed attack
grinding one account are both capped, without one noisy tenant exhausting the
shared anonymous bucket.
"""

from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)  # client IP (honours X-Forwarded-For)
        email = ""
        if isinstance(getattr(request, "data", None), dict):
            email = str(request.data.get("email", "")).strip().lower()
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{ident}:{email}",
        }
