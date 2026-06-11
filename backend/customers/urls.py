from rest_framework.routers import DefaultRouter

from customers import views

router = DefaultRouter()
router.register("customers", views.CustomerViewSet)
router.register("customer-preferences", views.CustomerPreferenceViewSet)
router.register("clinical-notes", views.ClinicalNoteViewSet)
router.register("customer-documents", views.CustomerDocumentViewSet)

urlpatterns = router.urls
