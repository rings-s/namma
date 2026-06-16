import { apiFetch, rows } from './client.js';
import { resource } from './resource.js';

/** analytics app — event stream, report definitions, metric rollups, goals. */

export const analyticsEvents = resource('analytics-events');
export const reports = resource('reports');
export const dailyMetrics = resource('daily-metrics');
export const dailyBranchMetrics = resource('daily-branch-metrics');
export const dailyEmployeeMetrics = resource('daily-employee-metrics');
export const goals = resource('goals');
export const goalMilestones = resource('goal-milestones');

/**
 * Top performers over a window (GET /daily-employee-metrics/leaderboard/).
 * @param {Record<string, any>} [params] @param {{ signal?: AbortSignal }} [opts]
 */
export function employeeLeaderboard(params, opts = {}) {
	return dailyEmployeeMetrics.collection('leaderboard', params, opts);
}

/**
 * Cancel a goal (POST /goals/{id}/cancel/). ACHIEVED/MISSED are not exposed —
 * there is no auto-transition endpoint yet, so the UI only offers Cancel.
 * @param {string} id
 */
export function cancelGoal(id) {
	return goals.do(id, 'cancel');
}

/**
 * Daily metrics. The backend scopes by org membership but offers no org query
 * param, so callers filter to the current organization client-side.
 * Named export retained for the dashboard.
 * @param {{ signal?: AbortSignal }} [opts]
 */
export async function listDailyMetrics(opts = {}) {
	return rows(await apiFetch('/daily-metrics/', { signal: opts.signal }));
}

/** Goals (each carries milestones + a computed progress_percent). @param {{ signal?: AbortSignal }} [opts] */
export async function listGoals(opts = {}) {
	return rows(await apiFetch('/goals/', { signal: opts.signal }));
}
