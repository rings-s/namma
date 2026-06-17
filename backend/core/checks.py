"""System checks that fail loudly on unsafe runtime configuration (audit V1).

The concurrency design across the platform — gap-free document numbering,
double-entry ledger posting, stock decrement, the ZATCA ICV/PIH chain, and the
refund/slot locks — all rely on ``select_for_update`` row-level locking. SQLite
silently ignores that locking, so running with DEBUG off on anything but
PostgreSQL would quietly void those guarantees. This check turns that silent
degradation into a startup error, so the planned move to PostgreSQL cannot be
skipped by accident.
"""

import sys

from django.conf import settings
from django.core.checks import Error, register

#: The only engine whose locking semantics the concurrency design assumes.
_REQUIRED_ENGINE = "django.db.backends.postgresql"


def _running_tests():
    """True under ``manage.py test`` (and pytest).

    Django's test runner forces ``DEBUG=False`` during system checks, but the
    suite deliberately runs on SQLite — this guard keeps the production check
    from blocking it while leaving it active for runserver/gunicorn/migrate.
    """
    argv = sys.argv
    return (len(argv) > 1 and argv[1] == "test") or argv[0].endswith("pytest")


def engine_errors():
    """The engine validation itself, independent of when it should run."""
    engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    if engine == _REQUIRED_ENGINE:
        return []
    return [
        Error(
            f"Database engine {engine!r} is configured with DEBUG=False.",
            hint=(
                "Set DATABASE_URL to a postgres:// DSN. select_for_update() is a "
                "no-op on SQLite, so document numbering, the ledger, stock "
                "movements and the ZATCA ICV chain would lose their concurrency "
                "guarantees in production."
            ),
            id="core.E001",
        )
    ]


@register()
def postgres_required_outside_debug(app_configs, **kwargs):
    if settings.DEBUG or _running_tests():
        return []
    return engine_errors()


__all__ = ["engine_errors", "postgres_required_outside_debug"]
