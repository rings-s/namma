import { PUBLIC_API_BASE } from '$env/static/public';
import { createApi } from '$lib/api/index.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, fetch, url }) {
  const api = createApi(PUBLIC_API_BASE, () => locals.accessToken, fetch);
  const page = Number(url.searchParams.get('page') ?? 1);
  const { data } = await api.operations.listAppointments({ page, page_size: 25 });
  return { appointments: data };
}
