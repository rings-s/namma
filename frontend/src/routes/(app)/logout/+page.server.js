import { redirect } from '@sveltejs/kit';
import { PUBLIC_API_BASE } from '$env/static/public';

/** @type {import('./$types').Actions} */
export const actions = {
  default: async ({ cookies, fetch, locals }) => {
    const token = locals.accessToken;
    const refresh = cookies.get('refresh_token');

    if (token && refresh) {
      try {
        await fetch(`${PUBLIC_API_BASE}/api/v1/auth/token/blacklist/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ refresh }),
        });
      } catch {
        // best-effort blacklist
      }
    }

    cookies.delete('access_token', { path: '/' });
    cookies.delete('refresh_token', { path: '/' });

    redirect(302, '/login');
  },
};
