import { PUBLIC_API_BASE } from '$env/static/public';
import { createApi } from '$lib/api/index.js';
import { error } from '@sveltejs/kit';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, fetch, params }) {
  const api = createApi(PUBLIC_API_BASE, () => locals.accessToken, fetch);

  const [customerRes, notesRes, appointmentsRes] = await Promise.all([
    api.customers.get(params.id),
    api.customers.listClinicalNotes({ customer: params.id }),
    api.operations.listAppointments({ customer: params.id, page_size: 10 }),
  ]);

  if (customerRes.error) error(customerRes.status ?? 404, customerRes.error.message);

  return {
    customer: customerRes.data,
    notes: notesRes.data,
    appointments: appointmentsRes.data,
  };
}
