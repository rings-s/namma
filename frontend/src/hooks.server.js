import { PUBLIC_API_BASE } from '$env/static/public';

/**
 * Decode a JWT payload without verifying the signature.
 * @param {string} token
 * @returns {Record<string,unknown> | null}
 */
function decodeJwt(token) {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = payload + '='.repeat((4 - (payload.length % 4)) % 4);
    return JSON.parse(atob(padded));
  } catch {
    return null;
  }
}

/**
 * Returns true if the token expires within the next 60 seconds.
 * @param {Record<string,unknown>} payload
 */
function isExpired(payload) {
  const exp = typeof payload['exp'] === 'number' ? payload['exp'] : 0;
  return Date.now() / 1000 >= exp - 60;
}

/** @type {import('@sveltejs/kit').Handle} */
export async function handle({ event, resolve }) {
  const accessToken = event.cookies.get('access_token') ?? null;
  const refreshToken = event.cookies.get('refresh_token') ?? null;

  let token = accessToken;
  let payload = token ? decodeJwt(token) : null;

  // Refresh if expired and we have a refresh token
  if ((!token || !payload || isExpired(payload)) && refreshToken) {
    try {
      const res = await event.fetch(`${PUBLIC_API_BASE}/api/v1/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken }),
      });

      if (res.ok) {
        const data = /** @type {Record<string,unknown>} */ (await res.json());
        const newToken = typeof data['access'] === 'string' ? data['access'] : null;
        if (newToken) {
          token = newToken;
          payload = decodeJwt(newToken);
          const secure = event.url.protocol === 'https:';
          event.cookies.set('access_token', newToken, {
            httpOnly: true,
            secure,
            sameSite: 'strict',
            path: '/',
            maxAge: 1800,
          });
        }
      } else {
        // Refresh failed — clear both cookies
        event.cookies.delete('access_token', { path: '/' });
        event.cookies.delete('refresh_token', { path: '/' });
        token = null;
        payload = null;
      }
    } catch {
      token = null;
      payload = null;
    }
  }

  event.locals.accessToken = token;
  event.locals.user = payload && !isExpired(payload) ? payload : null;

  return resolve(event);
}
