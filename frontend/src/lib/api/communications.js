/** @param {import('./client.js').createClient extends (...args: any[]) => infer R ? R : never} client */
export function communicationsApi(client) {
  return {
    // ── Message Templates ───────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listTemplates: (params) => client.get('/api/v1/message-templates/', { params }),
    /** @param {unknown} data */
    createTemplate: (data) => client.post('/api/v1/message-templates/', data),
    /** @param {string|number} id */
    getTemplate: (id) => client.get(`/api/v1/message-templates/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateTemplate: (id, data) => client.patch(`/api/v1/message-templates/${id}/`, data),
    /** @param {string|number} id */
    deleteTemplate: (id) => client.delete(`/api/v1/message-templates/${id}/`),

    // ── Message Dispatches ──────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listDispatches: (params) => client.get('/api/v1/message-dispatches/', { params }),
    /** @param {unknown} data */
    createDispatch: (data) => client.post('/api/v1/message-dispatches/', data),
    /** @param {string|number} id */
    sendDispatch: (id) => client.post(`/api/v1/message-dispatches/${id}/send/`),

    // ── Consent Records ─────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listConsents: (params) => client.get('/api/v1/consent-records/', { params }),
    /** @param {unknown} data */
    createConsent: (data) => client.post('/api/v1/consent-records/', data),

    // ── Email Events ────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listEmailEvents: (params) => client.get('/api/v1/email-events/', { params }),

    // ── Notifications ───────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listNotifications: (params) => client.get('/api/v1/notifications/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    listNotificationTemplates: (params) => client.get('/api/v1/notification-templates/', { params }),
    /** @param {unknown} data */
    createNotificationTemplate: (data) => client.post('/api/v1/notification-templates/', data),
    /** @param {string|number} id @param {unknown} data */
    updateNotificationTemplate: (id, data) => client.patch(`/api/v1/notification-templates/${id}/`, data),
    /** @param {string|number} id */
    deleteNotificationTemplate: (id) => client.delete(`/api/v1/notification-templates/${id}/`),

    // ── Conversations ───────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listConversations: (params) => client.get('/api/v1/conversations/', { params }),
    /** @param {unknown} data */
    createConversation: (data) => client.post('/api/v1/conversations/', data),
    /** @param {string|number} id */
    getConversation: (id) => client.get(`/api/v1/conversations/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateConversation: (id, data) => client.patch(`/api/v1/conversations/${id}/`, data),
    /** @param {string|number} id */
    deleteConversation: (id) => client.delete(`/api/v1/conversations/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    assignConversation: (id, data) => client.post(`/api/v1/conversations/${id}/assign/`, data),
    /** @param {string|number} id */
    resolveConversation: (id) => client.post(`/api/v1/conversations/${id}/resolve/`),
    /** @param {string|number} id */
    closeConversation: (id) => client.post(`/api/v1/conversations/${id}/close/`),

    // ── Conversation Messages ───────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listMessages: (params) => client.get('/api/v1/conversation-messages/', { params }),
    /** @param {unknown} data */
    createMessage: (data) => client.post('/api/v1/conversation-messages/', data),
  };
}
