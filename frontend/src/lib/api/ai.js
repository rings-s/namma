/** @param {import('./client.js').createClient extends (...args: any[]) => infer R ? R : never} client */
export function aiApi(client) {
  return {
    // ── AI Conversations ────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listConversations: (params) => client.get('/api/v1/ai-conversations/', { params }),
    /** @param {unknown} data */
    createConversation: (data) => client.post('/api/v1/ai-conversations/', data),
    /** @param {string|number} id */
    getConversation: (id) => client.get(`/api/v1/ai-conversations/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateConversation: (id, data) => client.patch(`/api/v1/ai-conversations/${id}/`, data),
    /** @param {string|number} id */
    deleteConversation: (id) => client.delete(`/api/v1/ai-conversations/${id}/`),

    // ── AI Messages ─────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listMessages: (params) => client.get('/api/v1/ai-messages/', { params }),
    /** @param {unknown} data */
    createMessage: (data) => client.post('/api/v1/ai-messages/', data),

    // ── AI Recommendations ──────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listRecommendations: (params) => client.get('/api/v1/ai-recommendations/', { params }),
    /** @param {string|number} id @param {unknown} data */
    updateRecommendation: (id, data) => client.patch(`/api/v1/ai-recommendations/${id}/`, data),
  };
}
