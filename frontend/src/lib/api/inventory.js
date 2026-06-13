/** @param {import('./client.js').createClient extends (...args: any[]) => infer R ? R : never} client */
export function inventoryApi(client) {
  return {
    // ── Stock Movements ─────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listMovements: (params) => client.get('/api/v1/stock-movements/', { params }),
    /** @param {unknown} data */
    createMovement: (data) => client.post('/api/v1/stock-movements/', data),

    // ── Stock Transfers ─────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listTransfers: (params) => client.get('/api/v1/stock-transfers/', { params }),
    /** @param {unknown} data */
    createTransfer: (data) => client.post('/api/v1/stock-transfers/', data),
    /** @param {string|number} id */
    getTransfer: (id) => client.get(`/api/v1/stock-transfers/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateTransfer: (id, data) => client.patch(`/api/v1/stock-transfers/${id}/`, data),
    /** @param {string|number} id */
    deleteTransfer: (id) => client.delete(`/api/v1/stock-transfers/${id}/`),

    // ── Suppliers ───────────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listSuppliers: (params) => client.get('/api/v1/suppliers/', { params }),
    /** @param {unknown} data */
    createSupplier: (data) => client.post('/api/v1/suppliers/', data),
    /** @param {string|number} id */
    getSupplier: (id) => client.get(`/api/v1/suppliers/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updateSupplier: (id, data) => client.patch(`/api/v1/suppliers/${id}/`, data),
    /** @param {string|number} id */
    deleteSupplier: (id) => client.delete(`/api/v1/suppliers/${id}/`),

    // ── Purchase Orders ─────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listPurchaseOrders: (params) => client.get('/api/v1/purchase-orders/', { params }),
    /** @param {unknown} data */
    createPurchaseOrder: (data) => client.post('/api/v1/purchase-orders/', data),
    /** @param {string|number} id */
    getPurchaseOrder: (id) => client.get(`/api/v1/purchase-orders/${id}/`),
    /** @param {string|number} id @param {unknown} data */
    updatePurchaseOrder: (id, data) => client.patch(`/api/v1/purchase-orders/${id}/`, data),
    /** @param {string|number} id */
    deletePurchaseOrder: (id) => client.delete(`/api/v1/purchase-orders/${id}/`),
    /** @param {string|number} id */
    submitOrder: (id) => client.post(`/api/v1/purchase-orders/${id}/submit/`),
    /** @param {string|number} id @param {unknown} data */
    receiveOrder: (id, data) => client.post(`/api/v1/purchase-orders/${id}/receive/`, data),

    // ── Purchase Order Lines ────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listOrderLines: (params) => client.get('/api/v1/purchase-order-lines/', { params }),
    /** @param {unknown} data */
    createOrderLine: (data) => client.post('/api/v1/purchase-order-lines/', data),
    /** @param {string|number} id @param {unknown} data */
    updateOrderLine: (id, data) => client.patch(`/api/v1/purchase-order-lines/${id}/`, data),
    /** @param {string|number} id */
    deleteOrderLine: (id) => client.delete(`/api/v1/purchase-order-lines/${id}/`),

    // ── Reorder Rules ───────────────────────────────────────────────────────
    /** @param {Record<string,string|number|boolean>} [params] */
    listReorderRules: (params) => client.get('/api/v1/reorder-rules/', { params }),
    /** @param {unknown} data */
    createReorderRule: (data) => client.post('/api/v1/reorder-rules/', data),
    /** @param {string|number} id @param {unknown} data */
    updateReorderRule: (id, data) => client.patch(`/api/v1/reorder-rules/${id}/`, data),
    /** @param {string|number} id */
    deleteReorderRule: (id) => client.delete(`/api/v1/reorder-rules/${id}/`),
    /** @param {Record<string,string|number|boolean>} [params] */
    lowStock: (params) => client.get('/api/v1/reorder-rules/low-stock/', { params }),
  };
}
