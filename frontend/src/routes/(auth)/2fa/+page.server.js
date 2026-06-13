import { fail, redirect } from '@sveltejs/kit';
import { PUBLIC_API_BASE } from '$env/static/public';

/** @type {import('./$types').Actions} */
export const actions = {
  default: async ({ request, cookies, fetch }) => {
    const form = await request.formData();
    const email = form.get('email')?.toString() ?? '';
    const password = form.get('password')?.toString() ?? '';
    const otp_code = form.get('otp_code')?.toString() ?? '';

    const res = await fetch(`${PUBLIC_API_BASE}/api/v1/auth/token/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, otp_code }),
    });

    const data = await res.json();

    if (!res.ok) {
      const detail = data?.detail ?? data?.otp_code?.[0] ?? 'Invalid code';
      return fail(res.status, { error: detail, email, password });
    }

    const secure = request.headers.get('x-forwarded-proto') === 'https';

    cookies.set('access_token', data.access, {
      httpOnly: true,
      secure,
      sameSite: 'strict',
      path: '/',
      maxAge: 1800,
    });

    cookies.set('refresh_token', data.refresh, {
      httpOnly: true,
      secure,
      sameSite: 'strict',
      path: '/',
      maxAge: 60 * 60 * 24 * 7,
    });

    redirect(302, '/dashboard');
  },
};
