/** @param {import('./client.js').createClient extends (...args: any[]) => infer R ? R : never} client */
export function integrationsApi(client) {
  return {
    // ── API Keys ────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listApiKeys: (params) => client.get('/api/v1/api-keys/', { params }),
    /** @param {unknown} data */
    createApiKey: (data) => client.post('/api/v1/api-keys/', data),
    /** @param {string|number} id @param {unknown} data */
    updateApiKey: (id, data) => client.patch(`/api/v1/api-keys/${id}/`, data),
    /** @param {string|number} id */
    deleteApiKey: (id) => client.delete(`/api/v1/api-keys/${id}/`),

    // ── Webhook Endpoints ───────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listWebhookEndpoints: (params) => client.get('/api/v1/webhook-endpoints/', { params }),
    /** @param {unknown} data */
    createWebhookEndpoint: (data) => client.post('/api/v1/webhook-endpoints/', data),
    /** @param {string|number} id */
    getWebhookEndpoint: (id) => client.get(`/api/v1/webhook-endpoints/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateWebhookEndpoint: (id, data) => client.patch(`/api/v1/webhook-endpoints/${id}/`, data),
    /** @param {string|number} id */
    deleteWebhookEndpoint: (id) => client.delete(`/api/v1/webhook-endpoints/${id}/`),

    // ── Devices ─────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listDevices: (params) => client.get('/api/v1/devices/', { params }),
    /** @param {unknown} data */
    createDevice: (data) => client.post('/api/v1/devices/', data),
    /** @param {string|number} id @param {unknown} data */
    updateDevice: (id, data) => client.patch(`/api/v1/devices/${id}/`, data),
    /** @param {string|number} id */
    deleteDevice: (id) => client.delete(`/api/v1/devices/${id}/`),

    // ── Sync Operations ─────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listSyncOperations: (params) => client.get('/api/v1/sync-operations/', { params }),
    /** @param {unknown} data */
    createSyncOperation: (data) => client.post('/api/v1/sync-operations/', data),

    // ── Outbound Events ─────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listOutboundEvents: (params) => client.get('/api/v1/outbound-events/', { params }),

    // ── Webhook Deliveries ──────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listWebhookDeliveries: (params) => client.get('/api/v1/webhook-deliveries/', { params }),
    /** @param {string|number} id */
    replayDelivery: (id) => client.post(`/api/v1/webhook-deliveries/${id}/replay/`),

    // ── Integration Connections ─────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listConnections: (params) => client.get('/api/v1/integration-connections/', { params }),
    /** @param {unknown} data */
    createConnection: (data) => client.post('/api/v1/integration-connections/', data),
    /** @param {string|number} id @param {unknown} data */
    updateConnection: (id, data) => client.patch(`/api/v1/integration-connections/${id}/`, data),
    /** @param {string|number} id */
    deleteConnection: (id) => client.delete(`/api/v1/integration-connections/${id}/`),
  };
}
