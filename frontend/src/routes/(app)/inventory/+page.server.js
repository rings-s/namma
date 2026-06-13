import { PUBLIC_API_BASE } from '$env/static/public';
import { createApi } from '$lib/api/index.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, fetch }) {
  const api = createApi(PUBLIC_API_BASE, () => locals.accessToken, fetch);
  const [productsRes, lowStockRes] = await Promise.all([
    api.commerce.listProducts({ page_size: 25 }),
    api.inventory.lowStock({}),
  ]);
  return { products: productsRes.data, lowStock: lowStockRes.data };
}
