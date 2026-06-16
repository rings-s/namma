import { resource } from './resource.js';

/**
 * operations app — staff, scheduling (appointments/bookings/events/tickets),
 * resources, queue, payroll & commissions, waitlist.
 */

export const employees = resource('employees');
export const employeeSchedules = resource('employee-schedules');
export const employeeServices = resource('employee-services');
export const employeeShifts = resource('employee-shifts');
export const recurrenceRules = resource('recurrence-rules');
export const events = resource('events');
export const appointments = resource('appointments');
export const appointmentReminders = resource('appointment-reminders');
export const bookings = resource('bookings');
export const bookingAttendees = resource('booking-attendees');
export const bookingDeposits = resource('booking-deposits');
export const ticketTypes = resource('ticket-types');
export const tickets = resource('tickets');
export const ticketVerifications = resource('ticket-verifications');
export const resources = resource('resources');
export const resourceSchedules = resource('resource-schedules');
export const slotHolds = resource('slot-holds');
export const cancellationPolicies = resource('cancellation-policies');
export const queueTickets = resource('queue-tickets');
export const payrollPeriods = resource('payroll-periods');
export const commissionEntries = resource('commission-entries');
export const commissionRules = resource('commission-rules');
export const employeeCostComponents = resource('employee-cost-components');
export const waitlistEntries = resource('waitlist-entries');

/** Fully-loaded hourly cost for an employee (GET /employees/{id}/loaded-cost/, manager+). @param {string} id @param {Record<string, any>} [params] */
export function employeeLoadedCost(id, params) {
	return employees.read(id, 'loaded-cost', params);
}

/** Aggregate labor summary across employees (GET /employees/labor-summary/, manager+). @param {Record<string, any>} [params] */
export function laborSummary(params) {
	return employees.collection('labor-summary', params);
}
