from rest_framework.routers import DefaultRouter

from customers import views

router = DefaultRouter()
router.register("customers", views.CustomerViewSet)
router.register("customer-preferences", views.CustomerPreferenceViewSet)
router.register("clinical-notes", views.ClinicalNoteViewSet)
router.register("customer-documents", views.CustomerDocumentViewSet)
router.register("customer-segments", views.CustomerSegmentViewSet)
router.register("customer-segment-memberships", views.CustomerSegmentMembershipViewSet)
router.register("surveys", views.SurveyViewSet)
router.register("survey-responses", views.SurveyResponseViewSet)

urlpatterns = router.urls
