/** @param {import('./client.js').createClient extends (...args: any[]) => infer R ? R : never} client */
export function operationsApi(client) {
  return {
    // ── Employees ───────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listEmployees: (params) => client.get('/api/v1/employees/', { params }),
    /** @param {unknown} data */
    createEmployee: (data) => client.post('/api/v1/employees/', data),
    /** @param {string|number} id */
    getEmployee: (id) => client.get(`/api/v1/employees/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateEmployee: (id, data) => client.patch(`/api/v1/employees/${id}/`, data),
    /** @param {string|number} id */
    deleteEmployee: (id) => client.delete(`/api/v1/employees/${id}/`),
    /** @param {string|number} id */
    loadedCost: (id) => client.get(`/api/v1/employees/${id}/loaded-cost/`),
    /** @param {Record<string,string|number|boolean>} [params] */
    laborSummary: (params) => client.get('/api/v1/employees/labor-summary/', { params }),

    // ── Employee Schedules ──────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listSchedules: (params) => client.get('/api/v1/employee-schedules/', { params }),
    /** @param {unknown} data */
    createSchedule: (data) => client.post('/api/v1/employee-schedules/', data),
    /** @param {string|number} id @param {unknown} data */
    updateSchedule: (id, data) => client.patch(`/api/v1/employee-schedules/${id}/`, data),
    /** @param {string|number} id */
    deleteSchedule: (id) => client.delete(`/api/v1/employee-schedules/${id}/`),

    // ── Employee Services ───────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listEmployeeServices: (params) => client.get('/api/v1/employee-services/', { params }),
    /** @param {unknown} data */
    createEmployeeService: (data) => client.post('/api/v1/employee-services/', data),
    /** @param {string|number} id @param {unknown} data */
    updateEmployeeService: (id, data) => client.patch(`/api/v1/employee-services/${id}/`, data),
    /** @param {string|number} id */
    deleteEmployeeService: (id) => client.delete(`/api/v1/employee-services/${id}/`),

    // ── Employee Shifts ─────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listShifts: (params) => client.get('/api/v1/employee-shifts/', { params }),
    /** @param {unknown} data */
    createShift: (data) => client.post('/api/v1/employee-shifts/', data),
    /** @param {string|number} id @param {unknown} data */
    updateShift: (id, data) => client.patch(`/api/v1/employee-shifts/${id}/`, data),
    /** @param {string|number} id */
    deleteShift: (id) => client.delete(`/api/v1/employee-shifts/${id}/`),

    // ── Recurrence Rules ────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listRecurrenceRules: (params) => client.get('/api/v1/recurrence-rules/', { params }),
    /** @param {unknown} data */
    createRecurrenceRule: (data) => client.post('/api/v1/recurrence-rules/', data),
    /** @param {string|number} id @param {unknown} data */
    updateRecurrenceRule: (id, data) => client.patch(`/api/v1/recurrence-rules/${id}/`, data),
    /** @param {string|number} id */
    deleteRecurrenceRule: (id) => client.delete(`/api/v1/recurrence-rules/${id}/`),

    // ── Events ──────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listEvents: (params) => client.get('/api/v1/events/', { params }),
    /** @param {unknown} data */
    createEvent: (data) => client.post('/api/v1/events/', data),
    /** @param {string|number} id */
    getEvent: (id) => client.get(`/api/v1/events/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateEvent: (id, data) => client.patch(`/api/v1/events/${id}/`, data),
    /** @param {string|number} id */
    deleteEvent: (id) => client.delete(`/api/v1/events/${id}/`),

    // ── Appointments ────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listAppointments: (params) => client.get('/api/v1/appointments/', { params }),
    /** @param {unknown} data */
    createAppointment: (data) => client.post('/api/v1/appointments/', data),
    /** @param {string|number} id */
    getAppointment: (id) => client.get(`/api/v1/appointments/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateAppointment: (id, data) => client.patch(`/api/v1/appointments/${id}/`, data),
    /** @param {string|number} id */
    deleteAppointment: (id) => client.delete(`/api/v1/appointments/${id}/`),

    // ── Appointment Reminders ───────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listReminders: (params) => client.get('/api/v1/appointment-reminders/', { params }),
    /** @param {unknown} data */
    createReminder: (data) => client.post('/api/v1/appointment-reminders/', data),
    /** @param {string|number} id @param {unknown} data */
    updateReminder: (id, data) => client.patch(`/api/v1/appointment-reminders/${id}/`, data),
    /** @param {string|number} id */
    deleteReminder: (id) => client.delete(`/api/v1/appointment-reminders/${id}/`),

    // ── Bookings ────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listBookings: (params) => client.get('/api/v1/bookings/', { params }),
    /** @param {unknown} data */
    createBooking: (data) => client.post('/api/v1/bookings/', data),
    /** @param {string|number} id */
    getBooking: (id) => client.get(`/api/v1/bookings/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateBooking: (id, data) => client.patch(`/api/v1/bookings/${id}/`, data),
    /** @param {string|number} id */
    deleteBooking: (id) => client.delete(`/api/v1/bookings/${id}/`),

    // ── Booking Attendees & Deposits ────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listAttendees: (params) => client.get('/api/v1/booking-attendees/', { params }),
    /** @param {unknown} data */
    createAttendee: (data) => client.post('/api/v1/booking-attendees/', data),
    /** @param {string|number} id @param {unknown} data */
    updateAttendee: (id, data) => client.patch(`/api/v1/booking-attendees/${id}/`, data),
    /** @param {string|number} id */
    deleteAttendee: (id) => client.delete(`/api/v1/booking-attendees/${id}/`),
    /** @param {Record<string,string|number|boolean>} [params] */
    listDeposits: (params) => client.get('/api/v1/booking-deposits/', { params }),
    /** @param {unknown} data */
    createDeposit: (data) => client.post('/api/v1/booking-deposits/', data),
    /** @param {string|number} id @param {unknown} data */
    updateDeposit: (id, data) => client.patch(`/api/v1/booking-deposits/${id}/`, data),
    /** @param {string|number} id */
    deleteDeposit: (id) => client.delete(`/api/v1/booking-deposits/${id}/`),

    // ── Ticket Types & Tickets ──────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listTicketTypes: (params) => client.get('/api/v1/ticket-types/', { params }),
    /** @param {unknown} data */
    createTicketType: (data) => client.post('/api/v1/ticket-types/', data),
    /** @param {string|number} id @param {unknown} data */
    updateTicketType: (id, data) => client.patch(`/api/v1/ticket-types/${id}/`, data),
    /** @param {string|number} id */
    deleteTicketType: (id) => client.delete(`/api/v1/ticket-types/${id}/`),
    /** @param {Record<string,string|number|boolean>} [params] */
    listTickets: (params) => client.get('/api/v1/tickets/', { params }),
    /** @param {unknown} data */
    createTicket: (data) => client.post('/api/v1/tickets/', data),
    /** @param {string|number} id @param {unknown} data */
    updateTicket: (id, data) => client.patch(`/api/v1/tickets/${id}/`, data),
    /** @param {string|number} id */
    deleteTicket: (id) => client.delete(`/api/v1/tickets/${id}/`),
    /** @param {unknown} data */
    verifyTicket: (data) => client.post('/api/v1/ticket-verifications/', data),

    // ── Resources ───────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listResources: (params) => client.get('/api/v1/resources/', { params }),
    /** @param {unknown} data */
    createResource: (data) => client.post('/api/v1/resources/', data),
    /** @param {string|number} id @param {unknown} data */
    updateResource: (id, data) => client.patch(`/api/v1/resources/${id}/`, data),
    /** @param {string|number} id */
    deleteResource: (id) => client.delete(`/api/v1/resources/${id}/`),
    /** @param {Record<string,string|number|boolean>} [params] */
    listResourceSchedules: (params) => client.get('/api/v1/resource-schedules/', { params }),
    /** @param {unknown} data */
    createResourceSchedule: (data) => client.post('/api/v1/resource-schedules/', data),
    /** @param {string|number} id @param {unknown} data */
    updateResourceSchedule: (id, data) => client.patch(`/api/v1/resource-schedules/${id}/`, data),
    /** @param {string|number} id */
    deleteResourceSchedule: (id) => client.delete(`/api/v1/resource-schedules/${id}/`),

    // ── Slot Holds ──────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listSlotHolds: (params) => client.get('/api/v1/slot-holds/', { params }),
    /** @param {unknown} data */
    createSlotHold: (data) => client.post('/api/v1/slot-holds/', data),
    /** @param {string|number} id */
    deleteSlotHold: (id) => client.delete(`/api/v1/slot-holds/${id}/`),

    // ── Cancellation Policies ───────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listCancellationPolicies: (params) => client.get('/api/v1/cancellation-policies/', { params }),
    /** @param {unknown} data */
    createCancellationPolicy: (data) => client.post('/api/v1/cancellation-policies/', data),
    /** @param {string|number} id @param {unknown} data */
    updateCancellationPolicy: (id, data) => client.patch(`/api/v1/cancellation-policies/${id}/`, data),
    /** @param {string|number} id */
    deleteCancellationPolicy: (id) => client.delete(`/api/v1/cancellation-policies/${id}/`),

    // ── Queue Tickets ───────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listQueueTickets: (params) => client.get('/api/v1/queue-tickets/', { params }),
    /** @param {unknown} data */
    createQueueTicket: (data) => client.post('/api/v1/queue-tickets/', data),
    /** @param {string|number} id @param {unknown} data */
    updateQueueTicket: (id, data) => client.patch(`/api/v1/queue-tickets/${id}/`, data),
    /** @param {string|number} id */
    deleteQueueTicket: (id) => client.delete(`/api/v1/queue-tickets/${id}/`),

    // ── Payroll ─────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listPayrollPeriods: (params) => client.get('/api/v1/payroll-periods/', { params }),
    /** @param {unknown} data */
    createPayrollPeriod: (data) => client.post('/api/v1/payroll-periods/', data),
    /** @param {string|number} id @param {unknown} data */
    updatePayrollPeriod: (id, data) => client.patch(`/api/v1/payroll-periods/${id}/`, data),
    /** @param {string|number} id */
    deletePayrollPeriod: (id) => client.delete(`/api/v1/payroll-periods/${id}/`),
    /** @param {Record<string,string|number|boolean>} [params] */
    listCommissionEntries: (params) => client.get('/api/v1/commission-entries/', { params }),

    // ── Commission Rules ────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listCommissionRules: (params) => client.get('/api/v1/commission-rules/', { params }),
    /** @param {unknown} data */
    createCommissionRule: (data) => client.post('/api/v1/commission-rules/', data),
    /** @param {string|number} id @param {unknown} data */
    updateCommissionRule: (id, data) => client.patch(`/api/v1/commission-rules/${id}/`, data),
    /** @param {string|number} id */
    deleteCommissionRule: (id) => client.delete(`/api/v1/commission-rules/${id}/`),

    // ── Employee Cost Components ────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listCostComponents: (params) => client.get('/api/v1/employee-cost-components/', { params }),
    /** @param {unknown} data */
    createCostComponent: (data) => client.post('/api/v1/employee-cost-components/', data),
    /** @param {string|number} id @param {unknown} data */
    updateCostComponent: (id, data) => client.patch(`/api/v1/employee-cost-components/${id}/`, data),
    /** @param {string|number} id */
    deleteCostComponent: (id) => client.delete(`/api/v1/employee-cost-components/${id}/`),

    // ── Waitlist ────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listWaitlistEntries: (params) => client.get('/api/v1/waitlist-entries/', { params }),
    /** @param {unknown} data */
    createWaitlistEntry: (data) => client.post('/api/v1/waitlist-entries/', data),
    /** @param {string|number} id @param {unknown} data */
    updateWaitlistEntry: (id, data) => client.patch(`/api/v1/waitlist-entries/${id}/`, data),
    /** @param {string|number} id */
    deleteWaitlistEntry: (id) => client.delete(`/api/v1/waitlist-entries/${id}/`),
  };
}
