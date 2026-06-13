import { PUBLIC_API_BASE } from '$env/static/public';
import { createApi } from '$lib/api/index.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, fetch }) {
  const api = createApi(PUBLIC_API_BASE, () => locals.accessToken, fetch);
  const [campaignsRes, promotionsRes] = await Promise.all([
    api.marketing.listCampaigns({ page_size: 10 }),
    api.marketing.listPromotions({ page_size: 10 }),
  ]);
  return { campaigns: campaignsRes.data, promotions: promotionsRes.data };
}
