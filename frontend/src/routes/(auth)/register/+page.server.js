import { fail, redirect } from '@sveltejs/kit';
import { PUBLIC_API_BASE } from '$env/static/public';

/** @type {import('./$types').Actions} */
export const actions = {
  default: async ({ request, fetch }) => {
    const form = await request.formData();

    const res = await fetch(`${PUBLIC_API_BASE}/api/v1/auth/register/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: form.get('email'),
        password: form.get('password'),
        first_name: form.get('first_name'),
        last_name: form.get('last_name'),
        phone: form.get('phone'),
      }),
    });

    if (!res.ok) {
      const data = await res.json();
      const detail =
        data?.detail ??
        data?.email?.[0] ??
        data?.password?.[0] ??
        data?.non_field_errors?.[0] ??
        'Registration failed';
      return fail(res.status, { error: detail });
    }

    redirect(302, '/login?registered=1');
  },
};
