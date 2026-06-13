import { PUBLIC_API_BASE } from '$env/static/public';
import { createApi } from '$lib/api/index.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, fetch }) {
  const api = createApi(PUBLIC_API_BASE, () => locals.accessToken, fetch);
  const [metricsRes, goalsRes, leaderboardRes] = await Promise.all([
    api.analytics.listDailyMetrics({ page_size: 7 }),
    api.analytics.listGoals({ page_size: 10 }),
    api.analytics.leaderboard({}),
  ]);
  return {
    metrics: metricsRes.data,
    goals: goalsRes.data,
    leaderboard: leaderboardRes.data,
  };
}
