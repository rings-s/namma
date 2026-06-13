/**
 * Organizations API module.
 * @module organizations
 */

/**
 * @param {import('./client.js').createClient extends (...args: any[]) => infer R ? R : never} client
 */
export function organizationsApi(client) {
  return {
    /** @param {Record<string,string|number|boolean>} [params] */
    list: (params) => client.get('/api/v1/organizations/', { params }),

    /** @param {unknown} data */
    create: (data) => client.post('/api/v1/organizations/', data),

    /** @param {string|number} id */
    get: (id) => client.get(`/api/v1/organizations/${id}/`),

    /** @param {string|number} id @param {unknown} data */
    update: (id, data) => client.patch(`/api/v1/organizations/${id}/`, data),

    /** @param {string|number} id */
    delete: (id) => client.delete(`/api/v1/organizations/${id}/`),

    /** @param {string|number} id */
    getSettings: (id) => client.get(`/api/v1/organization-settings/${id}/`),

    /** @param {string|number} id @param {unknown} data */
    updateSettings: (id, data) => client.patch(`/api/v1/organization-settings/${id}/`, data),

    /** @param {Record<string,string|number|boolean>} [params] */
    listBranches: (params) => client.get('/api/v1/branches/', { params }),

    /** @param {unknown} data */
    createBranch: (data) => client.post('/api/v1/branches/', data),

    /** @param {string|number} id */
    getBranch: (id) => client.get(`/api/v1/branches/${id}/`),

    /** @param {string|number} id @param {unknown} data */
    updateBranch: (id, data) => client.patch(`/api/v1/branches/${id}/`, data),

    /** @param {string|number} id */
    deleteBranch: (id) => client.delete(`/api/v1/branches/${id}/`),

    /** @param {Record<string,string|number|boolean>} [params] */
    listBranchHours: (params) => client.get('/api/v1/branch-hours/', { params }),

    /** @param {unknown} data */
    createBranchHour: (data) => client.post('/api/v1/branch-hours/', data),

    /** @param {string|number} id @param {unknown} data */
    updateBranchHour: (id, data) => client.patch(`/api/v1/branch-hours/${id}/`, data),

    /** @param {string|number} id */
    deleteBranchHour: (id) => client.delete(`/api/v1/branch-hours/${id}/`),

    /** @param {Record<string,string|number|boolean>} [params] */
    listRetentionPolicies: (params) => client.get('/api/v1/retention-policies/', { params }),

    /** @param {unknown} data */
    createRetentionPolicy: (data) => client.post('/api/v1/retention-policies/', data),

    /** @param {string|number} id @param {unknown} data */
    updateRetentionPolicy: (id, data) => client.patch(`/api/v1/retention-policies/${id}/`, data),

    /** @param {string|number} id */
    deleteRetentionPolicy: (id) => client.delete(`/api/v1/retention-policies/${id}/`),
  };
}
