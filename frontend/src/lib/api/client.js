/**
 * Base API client factory.
 * @module client
 */

/**
 * Strip trailing slash from a URL string.
 * @param {string} url
 * @returns {string}
 */
function stripTrailingSlash(url) {
  return url.endsWith('/') ? url.slice(0, -1) : url;
}

/**
 * Parse a response body safely.
 * @param {Response} res
 * @returns {Promise<unknown>}
 */
async function parseBody(res) {
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) {
    try {
      return await res.json();
    } catch {
      return null;
    }
  }
  try {
    return await res.text();
  } catch {
    return null;
  }
}

/**
 * Build an error object from a response.
 * @param {Response} res
 * @param {unknown} body
 * @returns {{ message: string; detail: unknown; status: number }}
 */
function buildError(res, body) {
  let message = `HTTP ${res.status}`;
  let detail = body;
  if (body && typeof body === 'object') {
    const b = /** @type {Record<string,unknown>} */ (body);
    if (typeof b['detail'] === 'string') message = b['detail'];
    else if (typeof b['message'] === 'string') message = b['message'];
    else if (typeof b['non_field_errors'] !== 'undefined') {
      const nfe = b['non_field_errors'];
      message = Array.isArray(nfe) ? nfe.join(', ') : String(nfe);
    }
  }
  return { message, detail, status: res.status };
}

/**
 * @typedef {{ signal?: AbortSignal; multipart?: boolean; params?: Record<string, string|number|boolean> }} RequestOptions
 * @typedef {{ data: unknown; error: null; status: number }} ApiSuccess
 * @typedef {{ data: null; error: { message: string; detail: unknown; status: number }; status: number }} ApiFailure
 * @typedef {ApiSuccess | ApiFailure} ApiResult
 */

/**
 * Create an API client.
 *
 * @param {string} baseUrl - Base URL without trailing slash.
 * @param {() => string | null} getToken - Returns the current access token (or null).
 * @param {typeof fetch} fetchFn - The fetch implementation to use.
 * @returns {{
 *   get: (path: string, opts?: RequestOptions) => Promise<ApiResult>,
 *   post: (path: string, body?: unknown, opts?: RequestOptions) => Promise<ApiResult>,
 *   patch: (path: string, body?: unknown, opts?: RequestOptions) => Promise<ApiResult>,
 *   put: (path: string, body?: unknown, opts?: RequestOptions) => Promise<ApiResult>,
 *   delete: (path: string, opts?: RequestOptions) => Promise<ApiResult>,
 * }}
 */
export function createClient(baseUrl, getToken, fetchFn) {
  const base = stripTrailingSlash(baseUrl);

  /** @type {string | null} */
  let cachedNewToken = null;

  /**
   * Attempt a token refresh using the refresh cookie.
   * @returns {Promise<string|null>} New access token or null.
   */
  async function refreshAccessToken() {
    try {
      const res = await fetchFn(`${base}/api/v1/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({}),
      });
      if (!res.ok) return null;
      const data = /** @type {Record<string,unknown>} */ (await res.json());
      return typeof data['access'] === 'string' ? data['access'] : null;
    } catch {
      return null;
    }
  }

  /**
   * Core request function.
   * @param {string} method
   * @param {string} path
   * @param {unknown} [body]
   * @param {RequestOptions} [opts]
   * @param {boolean} [isRetry]
   * @returns {Promise<ApiResult>}
   */
  async function request(method, path, body, opts = {}, isRetry = false) {
    const token = cachedNewToken ?? getToken();

    /** @type {Record<string,string>} */
    const headers = {};

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (body !== undefined && !opts.multipart) {
      headers['Content-Type'] = 'application/json';
    }

    let url = `${base}${path}`;
    if (opts.params) {
      const qs = new URLSearchParams(
        Object.entries(opts.params).map(([k, v]) => [k, String(v)])
      ).toString();
      if (qs) url += `?${qs}`;
    }

    /** @type {RequestInit} */
    const init = {
      method,
      headers,
      credentials: 'include',
    };

    if (opts.signal) init.signal = opts.signal;

    if (body !== undefined) {
      init.body = opts.multipart ? /** @type {BodyInit} */ (body) : JSON.stringify(body);
    }

    let res;
    try {
      res = await fetchFn(url, init);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Network error';
      return { data: null, error: { message, detail: null, status: 0 }, status: 0 };
    }

    // Handle 401: attempt refresh then retry once
    if (res.status === 401 && !isRetry) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        cachedNewToken = newToken;
        const retryHeaders = { ...headers, Authorization: `Bearer ${newToken}` };
        /** @type {RequestInit} */
        const retryInit = { ...init, headers: retryHeaders };
        let retryRes;
        try {
          retryRes = await fetchFn(url, retryInit);
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Network error';
          return { data: null, error: { message, detail: null, status: 0 }, status: 0 };
        }
        const retryBody = await parseBody(retryRes);
        if (retryRes.ok) {
          return { data: retryBody, error: null, status: retryRes.status };
        }
        return { data: null, error: buildError(retryRes, retryBody), status: retryRes.status };
      }
    }

    const responseBody = await parseBody(res);

    if (res.ok) {
      return { data: responseBody, error: null, status: res.status };
    }

    return { data: null, error: buildError(res, responseBody), status: res.status };
  }

  return {
    /** @param {string} path @param {RequestOptions} [opts] @returns {Promise<ApiResult>} */
    get: (path, opts) => request('GET', path, undefined, opts),

    /** @param {string} path @param {unknown} [body] @param {RequestOptions} [opts] @returns {Promise<ApiResult>} */
    post: (path, body, opts) => request('POST', path, body, opts),

    /** @param {string} path @param {unknown} [body] @param {RequestOptions} [opts] @returns {Promise<ApiResult>} */
    patch: (path, body, opts) => request('PATCH', path, body, opts),

    /** @param {string} path @param {unknown} [body] @param {RequestOptions} [opts] @returns {Promise<ApiResult>} */
    put: (path, body, opts) => request('PUT', path, body, opts),

    /** @param {string} path @param {RequestOptions} [opts] @returns {Promise<ApiResult>} */
    delete: (path, opts) => request('DELETE', path, undefined, opts),
  };
}
