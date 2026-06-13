import { PUBLIC_API_BASE } from '$env/static/public';
import { createApi } from '$lib/api/index.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, fetch }) {
  const api = createApi(PUBLIC_API_BASE, () => locals.accessToken, fetch);
  const [orgsRes, branchesRes] = await Promise.all([
    api.organizations.list({}),
    api.organizations.listBranches({}),
  ]);
  return { organizations: orgsRes.data, branches: branchesRes.data };
}
