/**
 * Accounts API module.
 * @module accounts
 */

/**
 * @param {import('./client.js').createClient extends (...args: any[]) => infer R ? R : never} client
 */
export function accountsApi(client) {
  return {
    /** @param {unknown} data */
    register: (data) => client.post('/api/v1/auth/register/', data),

    /** @param {unknown} data */
    login: (data) => client.post('/api/v1/auth/token/', data),

    /** @param {string} refreshToken */
    refresh: (refreshToken) =>
      client.post('/api/v1/auth/token/refresh/', { refresh: refreshToken }),

    logout: () => client.post('/api/v1/auth/token/blacklist/'),

    me: () => client.get('/api/v1/me/'),

    /** @param {unknown} data */
    updateMe: (data) => client.patch('/api/v1/me/', data),

    listSessions: () => client.get('/api/v1/auth/sessions/'),

    /** @param {string|number} id */
    revokeSession: (id) => client.post(`/api/v1/auth/sessions/${id}/revoke/`),

    setup2fa: () => client.post('/api/v1/auth/2fa/setup/'),

    /** @param {unknown} data */
    verify2fa: (data) => client.post('/api/v1/auth/2fa/verify/', data),

    /** @param {unknown} data */
    disable2fa: (data) => client.post('/api/v1/auth/2fa/disable/', data),

    /** @param {Record<string,string|number|boolean>} [params] */
    listRoles: (params) => client.get('/api/v1/user-roles/', { params }),

    /** @param {unknown} data */
    createRole: (data) => client.post('/api/v1/user-roles/', data),

    /** @param {string|number} id @param {unknown} data */
    updateRole: (id, data) => client.patch(`/api/v1/user-roles/${id}/`, data),

    /** @param {string|number} id */
    deleteRole: (id) => client.delete(`/api/v1/user-roles/${id}/`),
  };
}
