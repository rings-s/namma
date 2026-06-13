import { redirect } from '@sveltejs/kit';

/** @type {import('./$types').LayoutServerLoad} */
export async function load({ locals, url }) {
  if (!locals.user) {
    redirect(302, `/login?next=${encodeURIComponent(url.pathname)}`);
  }
  return { user: locals.user };
}
