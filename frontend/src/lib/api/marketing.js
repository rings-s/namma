/** @param {import('./client.js').createClient extends (...args: any[]) => infer R ? R : never} client */
export function marketingApi(client) {
  return {
    // ── Campaigns ───────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listCampaigns: (params) => client.get('/api/v1/campaigns/', { params }),
    /** @param {unknown} data */
    createCampaign: (data) => client.post('/api/v1/campaigns/', data),
    /** @param {string|number} id */
    getCampaign: (id) => client.get(`/api/v1/campaigns/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateCampaign: (id, data) => client.patch(`/api/v1/campaigns/${id}/`, data),
    /** @param {string|number} id */
    deleteCampaign: (id) => client.delete(`/api/v1/campaigns/${id}/`),
    /** @param {string|number} id */
    sendCampaign: (id) => client.post(`/api/v1/campaigns/${id}/send/`),
    /** @param {Record<string,string|number|boolean>} [params] */
    listCampaignRecipients: (params) => client.get('/api/v1/campaign-recipients/', { params }),

    // ── Promotions ──────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listPromotions: (params) => client.get('/api/v1/promotions/', { params }),
    /** @param {unknown} data */
    createPromotion: (data) => client.post('/api/v1/promotions/', data),
    /** @param {string|number} id */
    getPromotion: (id) => client.get(`/api/v1/promotions/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updatePromotion: (id, data) => client.patch(`/api/v1/promotions/${id}/`, data),
    /** @param {string|number} id */
    deletePromotion: (id) => client.delete(`/api/v1/promotions/${id}/`),

    // ── Loyalty Programs ────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listLoyaltyPrograms: (params) => client.get('/api/v1/loyalty-programs/', { params }),
    /** @param {unknown} data */
    createLoyaltyProgram: (data) => client.post('/api/v1/loyalty-programs/', data),
    /** @param {string|number} id @param {unknown} data */
    updateLoyaltyProgram: (id, data) => client.patch(`/api/v1/loyalty-programs/${id}/`, data),
    /** @param {string|number} id */
    deleteLoyaltyProgram: (id) => client.delete(`/api/v1/loyalty-programs/${id}/`),
    /** @param {Record<string,string|number|boolean>} [params] */
    listLoyaltyTransactions: (params) => client.get('/api/v1/loyalty-transactions/', { params }),

    // ── Referrals ───────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listReferralPrograms: (params) => client.get('/api/v1/referral-programs/', { params }),
    /** @param {unknown} data */
    createReferralProgram: (data) => client.post('/api/v1/referral-programs/', data),
    /** @param {string|number} id @param {unknown} data */
    updateReferralProgram: (id, data) => client.patch(`/api/v1/referral-programs/${id}/`, data),
    /** @param {string|number} id */
    deleteReferralProgram: (id) => client.delete(`/api/v1/referral-programs/${id}/`),
    /** @param {Record<string,string|number|boolean>} [params] */
    listReferrals: (params) => client.get('/api/v1/referrals/', { params }),
    /** @param {unknown} data */
    createReferral: (data) => client.post('/api/v1/referrals/', data),
    /** @param {string|number} id @param {unknown} data */
    qualifyReferral: (id, data) => client.post(`/api/v1/referrals/${id}/qualify/`, data),

    // ── Journeys ────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listJourneys: (params) => client.get('/api/v1/journeys/', { params }),
    /** @param {unknown} data */
    createJourney: (data) => client.post('/api/v1/journeys/', data),
    /** @param {string|number} id @param {unknown} data */
    updateJourney: (id, data) => client.patch(`/api/v1/journeys/${id}/`, data),
    /** @param {string|number} id */
    deleteJourney: (id) => client.delete(`/api/v1/journeys/${id}/`),
    /** @param {Record<string,string|number|boolean>} [params] */
    listJourneySteps: (params) => client.get('/api/v1/journey-steps/', { params }),
    /** @param {unknown} data */
    createJourneyStep: (data) => client.post('/api/v1/journey-steps/', data),
    /** @param {string|number} id @param {unknown} data */
    updateJourneyStep: (id, data) => client.patch(`/api/v1/journey-steps/${id}/`, data),
    /** @param {string|number} id */
    deleteJourneyStep: (id) => client.delete(`/api/v1/journey-steps/${id}/`),
  };
}
