/** @param {import('./client.js').createClient extends (...args: any[]) => infer R ? R : never} client */
export function coreApi(client) {
  return {
    /** @param {Record<string,string|number|boolean>} [params] */
    listCountries: (params) => client.get('/api/v1/countries/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    listCurrencies: (params) => client.get('/api/v1/currencies/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    listTranslations: (params) => client.get('/api/v1/translations/', { params }),
    /** @param {unknown} data */
    createTranslation: (data) => client.post('/api/v1/translations/', data),
    /** @param {string|number} id @param {unknown} data */
    updateTranslation: (id, data) => client.patch(`/api/v1/translations/${id}/`, data),
    /** @param {string|number} id */
    deleteTranslation: (id) => client.delete(`/api/v1/translations/${id}/`),
    /** @param {Record<string,string|number|boolean>} [params] */
    listAuditLogs: (params) => client.get('/api/v1/audit-logs/', { params }),
    /** @param {Record<string,string|number|boolean>} [params] */
    listAccessLogs: (params) => client.get('/api/v1/access-logs/', { params }),
  };
}
