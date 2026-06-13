/** @param {import('./client.js').createClient extends (...args: any[]) => infer R ? R : never} client */
export function commerceApi(client) {
  return {
    // ── Service Categories ──────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listCategories: (params) => client.get('/api/v1/service-categories/', { params }),
    /** @param {unknown} data */
    createCategory: (data) => client.post('/api/v1/service-categories/', data),
    /** @param {string|number} id */
    getCategory: (id) => client.get(`/api/v1/service-categories/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateCategory: (id, data) => client.patch(`/api/v1/service-categories/${id}/`, data),
    /** @param {string|number} id */
    deleteCategory: (id) => client.delete(`/api/v1/service-categories/${id}/`),

    // ── Services ────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listServices: (params) => client.get('/api/v1/services/', { params }),
    /** @param {unknown} data */
    createService: (data) => client.post('/api/v1/services/', data),
    /** @param {string|number} id */
    getService: (id) => client.get(`/api/v1/services/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateService: (id, data) => client.patch(`/api/v1/services/${id}/`, data),
    /** @param {string|number} id */
    deleteService: (id) => client.delete(`/api/v1/services/${id}/`),

    // ── Products ────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listProducts: (params) => client.get('/api/v1/products/', { params }),
    /** @param {unknown} data */
    createProduct: (data) => client.post('/api/v1/products/', data),
    /** @param {string|number} id */
    getProduct: (id) => client.get(`/api/v1/products/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateProduct: (id, data) => client.patch(`/api/v1/products/${id}/`, data),
    /** @param {string|number} id */
    deleteProduct: (id) => client.delete(`/api/v1/products/${id}/`),

    // ── Sales ───────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listSales: (params) => client.get('/api/v1/sales/', { params }),
    /** @param {unknown} data */
    createSale: (data) => client.post('/api/v1/sales/', data),
    /** @param {string|number} id */
    getSale: (id) => client.get(`/api/v1/sales/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateSale: (id, data) => client.patch(`/api/v1/sales/${id}/`, data),
    /** @param {string|number} id */
    deleteSale: (id) => client.delete(`/api/v1/sales/${id}/`),
    /** @param {string|number} id */
    saleCommissions: (id) => client.post(`/api/v1/sales/${id}/commissions/`),

    // ── Sale Items ──────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listSaleItems: (params) => client.get('/api/v1/sale-items/', { params }),
    /** @param {unknown} data */
    createSaleItem: (data) => client.post('/api/v1/sale-items/', data),
    /** @param {string|number} id @param {unknown} data */
    updateSaleItem: (id, data) => client.patch(`/api/v1/sale-items/${id}/`, data),
    /** @param {string|number} id */
    deleteSaleItem: (id) => client.delete(`/api/v1/sale-items/${id}/`),

    // ── Gift Cards ──────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listGiftCards: (params) => client.get('/api/v1/gift-cards/', { params }),
    /** @param {unknown} data */
    createGiftCard: (data) => client.post('/api/v1/gift-cards/', data),
    /** @param {string|number} id */
    getGiftCard: (id) => client.get(`/api/v1/gift-cards/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateGiftCard: (id, data) => client.patch(`/api/v1/gift-cards/${id}/`, data),
    /** @param {string|number} id @param {unknown} data */
    redeemGiftCard: (id, data) => client.post(`/api/v1/gift-cards/${id}/redeem/`, data),
    /** @param {Record<string,string|number|boolean>} [params] */
    listGiftCardTransactions: (params) => client.get('/api/v1/gift-card-transactions/', { params }),

    // ── Store Credit ────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listStoreCreditAccounts: (params) => client.get('/api/v1/store-credit-accounts/', { params }),
    /** @param {unknown} data */
    createStoreCreditAccount: (data) => client.post('/api/v1/store-credit-accounts/', data),
    /** @param {string|number} id @param {unknown} data */
    adjustStoreCredit: (id, data) => client.post(`/api/v1/store-credit-accounts/${id}/adjust/`, data),
    /** @param {Record<string,string|number|boolean>} [params] */
    listStoreCreditTransactions: (params) => client.get('/api/v1/store-credit-transactions/', { params }),

    // ── Packages ────────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listPackages: (params) => client.get('/api/v1/packages/', { params }),
    /** @param {unknown} data */
    createPackage: (data) => client.post('/api/v1/packages/', data),
    /** @param {string|number} id */
    getPackage: (id) => client.get(`/api/v1/packages/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updatePackage: (id, data) => client.patch(`/api/v1/packages/${id}/`, data),
    /** @param {string|number} id */
    deletePackage: (id) => client.delete(`/api/v1/packages/${id}/`),

    // ── Package Items ───────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listPackageItems: (params) => client.get('/api/v1/package-items/', { params }),
    /** @param {unknown} data */
    createPackageItem: (data) => client.post('/api/v1/package-items/', data),
    /** @param {string|number} id @param {unknown} data */
    updatePackageItem: (id, data) => client.patch(`/api/v1/package-items/${id}/`, data),
    /** @param {string|number} id */
    deletePackageItem: (id) => client.delete(`/api/v1/package-items/${id}/`),

    // ── Customer Packages ───────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listCustomerPackages: (params) => client.get('/api/v1/customer-packages/', { params }),
    /** @param {unknown} data */
    createCustomerPackage: (data) => client.post('/api/v1/customer-packages/', data),
    /** @param {string|number} id @param {unknown} data */
    redeemCustomerPackage: (id, data) => client.post(`/api/v1/customer-packages/${id}/redeem/`, data),
    /** @param {Record<string,string|number|boolean>} [params] */
    listPackageRedemptions: (params) => client.get('/api/v1/package-redemptions/', { params }),

    // ── Pricing Rules ───────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listPricingRules: (params) => client.get('/api/v1/pricing-rules/', { params }),
    /** @param {unknown} data */
    createPricingRule: (data) => client.post('/api/v1/pricing-rules/', data),
    /** @param {string|number} id @param {unknown} data */
    updatePricingRule: (id, data) => client.patch(`/api/v1/pricing-rules/${id}/`, data),
    /** @param {string|number} id */
    deletePricingRule: (id) => client.delete(`/api/v1/pricing-rules/${id}/`),
    /** @param {unknown} data */
    priceQuote: (data) => client.post('/api/v1/pricing-rules/quote/', data),
  };
}
