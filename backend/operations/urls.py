from rest_framework.routers import DefaultRouter

from operations import views

router = DefaultRouter()
router.register("employees", views.EmployeeViewSet)
router.register("employee-schedules", views.EmployeeScheduleViewSet)
router.register("employee-services", views.EmployeeServiceViewSet)
router.register("employee-shifts", views.EmployeeShiftViewSet)
router.register("recurrence-rules", views.RecurrenceRuleViewSet)
router.register("events", views.EventViewSet)
router.register("appointments", views.AppointmentViewSet)
router.register("appointment-reminders", views.AppointmentReminderViewSet)
router.register("bookings", views.BookingViewSet)
router.register("booking-attendees", views.BookingAttendeeViewSet)
router.register("booking-deposits", views.BookingDepositViewSet)
router.register("ticket-types", views.TicketTypeViewSet)
router.register("tickets", views.TicketViewSet)
router.register("ticket-verifications", views.TicketVerificationViewSet)
router.register("resources", views.ResourceViewSet)
router.register("resource-schedules", views.ResourceScheduleViewSet)
router.register("slot-holds", views.SlotHoldViewSet)
router.register("cancellation-policies", views.CancellationPolicyViewSet)
router.register("queue-tickets", views.QueueTicketViewSet)
router.register("payroll-periods", views.PayrollPeriodViewSet)
router.register("commission-entries", views.CommissionEntryViewSet)
router.register("commission-rules", views.CommissionRuleViewSet)
router.register("employee-cost-components", views.EmployeeCostComponentViewSet)
router.register("waitlist-entries", views.WaitlistEntryViewSet)

urlpatterns = router.urls
