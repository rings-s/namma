import { PUBLIC_API_BASE } from '$env/static/public';
import { createApi } from '$lib/api/index.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, fetch }) {
  const api = createApi(PUBLIC_API_BASE, () => locals.accessToken, fetch);

  const [metricsRes, appointmentsRes] = await Promise.all([
    api.analytics.listDailyMetrics({ page_size: 1 }),
    api.operations.listAppointments({ page_size: 5 }),
  ]);

  return {
    metrics: metricsRes.data ?? null,
    appointments: appointmentsRes.data ?? null,
  };
}
