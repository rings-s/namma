/**
 * Customers API module.
 * @module customers
 */

/**
 * @param {import('./client.js').createClient extends (...args: any[]) => infer R ? R : never} client
 */
export function customersApi(client) {
  return {
    // ── Customers ──────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    list: (params) => client.get('/api/v1/customers/', { params }),

    /** @param {unknown} data */
    create: (data) => client.post('/api/v1/customers/', data),

    /** @param {string|number} id */
    get: (id) => client.get(`/api/v1/customers/${id}/`),

    /** @param {string|number} id @param {unknown} data */
    update: (id, data) => client.patch(`/api/v1/customers/${id}/`, data),

    /** @param {string|number} id */
    delete: (id) => client.delete(`/api/v1/customers/${id}/`),

    /** @param {string|number} id */
    pdplExport: (id) => client.get(`/api/v1/customers/${id}/pdpl-export/`),

    /** @param {string|number} id */
    pdplErase: (id) => client.post(`/api/v1/customers/${id}/pdpl-erase/`),

    // ── Customer Preferences ────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listPreferences: (params) => client.get('/api/v1/customer-preferences/', { params }),

    /** @param {unknown} data */
    createPreference: (data) => client.post('/api/v1/customer-preferences/', data),

    /** @param {string|number} id @param {unknown} data */
    updatePreference: (id, data) => client.patch(`/api/v1/customer-preferences/${id}/`, data),

    /** @param {string|number} id */
    deletePreference: (id) => client.delete(`/api/v1/customer-preferences/${id}/`),

    // ── Clinical Notes ──────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listClinicalNotes: (params) => client.get('/api/v1/clinical-notes/', { params }),

    /** @param {unknown} data */
    createClinicalNote: (data) => client.post('/api/v1/clinical-notes/', data),

    /** @param {string|number} id */
    getClinicalNote: (id) => client.get(`/api/v1/clinical-notes/${id}/`),

    /** @param {string|number} id @param {unknown} data */
    updateClinicalNote: (id, data) => client.patch(`/api/v1/clinical-notes/${id}/`, data),

    /** @param {string|number} id */
    deleteClinicalNote: (id) => client.delete(`/api/v1/clinical-notes/${id}/`),

    // ── Customer Documents ──────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listDocuments: (params) => client.get('/api/v1/customer-documents/', { params }),

    /** @param {unknown} data */
    createDocument: (data) => client.post('/api/v1/customer-documents/', data),

    /** @param {string|number} id */
    getDocument: (id) => client.get(`/api/v1/customer-documents/${id}/`),

    /** @param {string|number} id */
    deleteDocument: (id) => client.delete(`/api/v1/customer-documents/${id}/`),

    // ── Customer Segments ───────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listSegments: (params) => client.get('/api/v1/customer-segments/', { params }),

    /** @param {unknown} data */
    createSegment: (data) => client.post('/api/v1/customer-segments/', data),

    /** @param {string|number} id */
    getSegment: (id) => client.get(`/api/v1/customer-segments/${id}/`),

    /** @param {string|number} id @param {unknown} data */
    updateSegment: (id, data) => client.patch(`/api/v1/customer-segments/${id}/`, data),

    /** @param {string|number} id */
    deleteSegment: (id) => client.delete(`/api/v1/customer-segments/${id}/`),

    /** @param {string|number} id */
    refreshSegment: (id) => client.post(`/api/v1/customer-segments/${id}/refresh/`),

    // ── Segment Memberships ─────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listSegmentMemberships: (params) => client.get('/api/v1/customer-segment-memberships/', { params }),

    /** @param {unknown} data */
    createSegmentMembership: (data) => client.post('/api/v1/customer-segment-memberships/', data),

    /** @param {string|number} id */
    deleteSegmentMembership: (id) => client.delete(`/api/v1/customer-segment-memberships/${id}/`),

    // ── Surveys ─────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listSurveys: (params) => client.get('/api/v1/surveys/', { params }),

    /** @param {unknown} data */
    createSurvey: (data) => client.post('/api/v1/surveys/', data),

    /** @param {string|number} id */
    getSurvey: (id) => client.get(`/api/v1/surveys/${id}/`),

    /** @param {string|number} id @param {unknown} data */
    updateSurvey: (id, data) => client.patch(`/api/v1/surveys/${id}/`, data),

    /** @param {string|number} id */
    deleteSurvey: (id) => client.delete(`/api/v1/surveys/${id}/`),

    // ── Survey Responses ────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listSurveyResponses: (params) => client.get('/api/v1/survey-responses/', { params }),

    /** @param {unknown} data */
    createSurveyResponse: (data) => client.post('/api/v1/survey-responses/', data),

    /** @param {string|number} id */
    surveyNps: (id) => client.get(`/api/v1/survey-responses/${id}/nps/`),
  };
}
