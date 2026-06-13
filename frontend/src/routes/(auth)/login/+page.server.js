import { fail, redirect } from '@sveltejs/kit';
import { PUBLIC_API_BASE } from '$env/static/public';

/** @type {import('./$types').Actions} */
export const actions = {
  default: async ({ request, cookies, fetch, url }) => {
    const form = await request.formData();
    const email = form.get('email')?.toString() ?? '';
    const password = form.get('password')?.toString() ?? '';
    const otp_code = form.get('otp_code')?.toString() ?? undefined;

    const body = /** @type {Record<string,string>} */ ({ email, password });
    if (otp_code) body['otp_code'] = otp_code;

    const res = await fetch(`${PUBLIC_API_BASE}/api/v1/auth/token/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      const detail = data?.detail ?? data?.non_field_errors?.[0] ?? 'Invalid credentials';
      // Backend signals 2FA is required
      if (res.status === 400 && detail?.toLowerCase?.().includes('otp')) {
        redirect(302, `/2fa?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`);
      }
      return fail(res.status, { error: detail });
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

    const next = url.searchParams.get('next') ?? '/dashboard';
    redirect(302, next);
  },
};
