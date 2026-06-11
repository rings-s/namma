"""Platform-wide API sanity checks."""

from django.test import TestCase
from django.urls import URLResolver, get_resolver
from rest_framework.routers import DefaultRouter


def iter_registered_viewsets():
    """Yield every viewset registered on any router mounted under /api/v1/."""
    seen = set()
    for pattern in get_resolver().url_patterns:
        if not isinstance(pattern, URLResolver):
            continue
        module = getattr(pattern.urlconf_module, "__name__", "")
        if not hasattr(pattern.urlconf_module, "router"):
            continue
        router = pattern.urlconf_module.router
        if isinstance(router, DefaultRouter):
            for prefix, viewset, basename in router.registry:
                if viewset not in seen:
                    seen.add(viewset)
                    yield prefix, viewset


class SerializerConfigurationTests(TestCase):
    """Force-build every serializer so bad Meta configs fail loudly in CI."""

    def test_every_registered_serializer_builds(self):
        checked = 0
        for prefix, viewset in iter_registered_viewsets():
            serializer_class = viewset.serializer_class
            with self.subTest(resource=prefix, serializer=serializer_class.__name__):
                # Accessing .fields triggers full field/Meta validation.
                self.assertTrue(len(serializer_class().fields) > 0)
            checked += 1
        self.assertGreater(checked, 50, "expected the full API surface to be registered")

    def test_every_tenant_viewset_queryset_is_evaluable(self):
        # Catches typos in select_related / org_field paths at test time.
        for prefix, viewset in iter_registered_viewsets():
            with self.subTest(resource=prefix, viewset=viewset.__name__):
                list(viewset.queryset.all()[:1])
