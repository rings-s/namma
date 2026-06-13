/** @param {import('./client.js').createClient extends (...args: any[]) => infer R ? R : never} client */
export function analyticsApi(client) {
  return {
    // ── Events ──────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listEvents: (params) => client.get('/api/v1/analytics-events/', { params }),
    /** @param {unknown} data */
    createEvent: (data) => client.post('/api/v1/analytics-events/', data),

    // ── Reports ─────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listReports: (params) => client.get('/api/v1/reports/', { params }),
    /** @param {unknown} data */
    createReport: (data) => client.post('/api/v1/reports/', data),
    /** @param {string|number} id */
    getReport: (id) => client.get(`/api/v1/reports/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateReport: (id, data) => client.patch(`/api/v1/reports/${id}/`, data),
    /** @param {string|number} id */
    deleteReport: (id) => client.delete(`/api/v1/reports/${id}/`),

    // ── Daily Metrics ───────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listDailyMetrics: (params) => client.get('/api/v1/daily-metrics/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    listBranchMetrics: (params) => client.get('/api/v1/daily-branch-metrics/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    listEmployeeMetrics: (params) => client.get('/api/v1/daily-employee-metrics/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    leaderboard: (params) => client.get('/api/v1/daily-employee-metrics/leaderboard/', { params }),

    // ── Goals ───────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listGoals: (params) => client.get('/api/v1/goals/', { params }),
    /** @param {unknown} data */
    createGoal: (data) => client.post('/api/v1/goals/', data),
    /** @param {string|number} id */
    getGoal: (id) => client.get(`/api/v1/goals/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateGoal: (id, data) => client.patch(`/api/v1/goals/${id}/`, data),
    /** @param {string|number} id */
    deleteGoal: (id) => client.delete(`/api/v1/goals/${id}/`),
    /** @param {string|number} id */
    cancelGoal: (id) => client.post(`/api/v1/goals/${id}/cancel/`),

    // ── Goal Milestones ─────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listMilestones: (params) => client.get('/api/v1/goal-milestones/', { params }),
    /** @param {unknown} data */
    createMilestone: (data) => client.post('/api/v1/goal-milestones/', data),
    /** @param {string|number} id @param {unknown} data */
    updateMilestone: (id, data) => client.patch(`/api/v1/goal-milestones/${id}/`, data),
    /** @param {string|number} id */
    deleteMilestone: (id) => client.delete(`/api/v1/goal-milestones/${id}/`),
  };
}
