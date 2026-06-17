"""API-key authentication (audit gap V4).

The ``APIKey`` model was issue-complete (prefix lookup handle + SHA-256 hash +
scopes + expiry + ``is_active``) but nothing verified it, so the issuance
endpoint was a live, half-built auth surface. This closes the verification side.

An API key authenticates an *organization service principal*, never a person:
there is no ``accounts.User`` behind it. :class:`APIKeyUser` therefore satisfies
``IsAuthenticated`` and carries ``organization_id`` (so the tenant-scoping mixin
can scope queries to the key's org), but holds no ``UserRole`` — meaning every
``require_org_role`` gate denies it by default (least privilege). Widening that
to honour ``APIKey.scopes`` is a deliberate later step, not an implicit one.
"""

from datetime import timedelta

import hmac

from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import authentication, exceptions

from integrations.models import APIKey
from integrations.services import hash_key

#: ``Authorization: Api-Key <plaintext>`` keyword (an alternative to the
#: ``X-Api-Key`` header). Distinct from JWT's ``Bearer`` so the two
#: authenticators never contend for the same credential.
KEYWORD = "Api-Key"

#: ``last_used_at`` is refreshed at most this often, so per-request auth does not
#: turn every read into a write.
_LAST_USED_REFRESH = timedelta(seconds=60)


class APIKeyUser:
    """Authenticated principal standing in for an organization's API key.

    Intentionally not a model instance: ``pk``/``id`` are ``None`` so code that
    keys off a real user row (idempotency records, audit actor, user throttle)
    treats it as having no user — never crashing, never impersonating a person.
    """

    is_active = True
    is_staff = False
    is_superuser = False
    pk = None
    id = None

    def __init__(self, api_key):
        self.api_key = api_key
        self.organization_id = api_key.organization_id

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __str__(self):
        return f"APIKey:{self.api_key.key_prefix}"


class APIKeyAuthentication(authentication.BaseAuthentication):
    """Verify a presented API key against its stored hash, expiry and status.

    Returns ``None`` (declines, letting the next authenticator run) when no API
    key credential is present, so JWT and the browsable-API session auth are
    unaffected. Raises ``AuthenticationFailed`` only when an API-key credential
    *is* presented but is invalid.
    """

    def authenticate(self, request):
        plaintext = self._extract_key(request)
        if not plaintext:
            return None
        api_key = (
            APIKey.objects.select_related("organization")
            .filter(key_prefix=plaintext[:8], is_active=True)
            .first()
        )
        # Constant-time hash comparison; a missing row still does one compare so
        # presence/absence of a prefix is not timing-distinguishable.
        expected = api_key.key_hash if api_key is not None else ""
        if not hmac.compare_digest(expected, hash_key(plaintext)) or api_key is None:
            raise exceptions.AuthenticationFailed("Invalid API key.")
        if api_key.expires_at is not None and api_key.expires_at <= timezone.now():
            raise exceptions.AuthenticationFailed("This API key has expired.")
        self._touch(api_key)
        return (APIKeyUser(api_key), api_key)

    def authenticate_header(self, request):
        # Drives the WWW-Authenticate header so failures answer 401, not 403.
        return KEYWORD

    @staticmethod
    def _extract_key(request):
        header_key = request.META.get("HTTP_X_API_KEY", "").strip()
        if header_key:
            return header_key
        parts = request.META.get("HTTP_AUTHORIZATION", "").split()
        if len(parts) == 2 and parts[0].lower() == KEYWORD.lower():
            return parts[1].strip()
        return ""

    @staticmethod
    def _touch(api_key):
        now = timezone.now()
        if (
            api_key.last_used_at is None
            or now - api_key.last_used_at > _LAST_USED_REFRESH
        ):
            APIKey.objects.filter(pk=api_key.pk).update(last_used_at=now)


class APIKeyAuthenticationScheme(OpenApiAuthenticationExtension):
    """Surfaces the API-key header as a security scheme in the OpenAPI doc."""

    target_class = "integrations.authentication.APIKeyAuthentication"
    name = "ApiKeyAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "apiKey", "in": "header", "name": "X-Api-Key"}


__all__ = ["APIKeyAuthentication", "APIKeyUser", "KEYWORD"]
