// Auth state lives in localStorage and every screen calls the API from the
// browser, so we render client-side only. This keeps token handling and the
// RTL document flip free of SSR hydration mismatches.
export const ssr = false;
