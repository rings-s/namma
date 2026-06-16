import { resource } from './resource.js';

/** inventory app — append-only stock movements, transfers, suppliers, purchasing, reorder rules. */

export const stockMovements = resource('stock-movements');
export const stockTransfers = resource('stock-transfers');
export const suppliers = resource('suppliers');
export const purchaseOrders = resource('purchase-orders');
export const purchaseOrderLines = resource('purchase-order-lines');
export const reorderRules = resource('reorder-rules');

/** Submit a draft purchase order to the supplier (POST /purchase-orders/{id}/submit/). @param {string} id */
export function submitPurchaseOrder(id) {
	return purchaseOrders.do(id, 'submit');
}

/** Receive (partial) lines against a PO (POST /purchase-orders/{id}/receive/). @param {string} id @param {Record<string, any>} [body] */
export function receivePurchaseOrder(id, body) {
	return purchaseOrders.do(id, 'receive', body);
}

/** Items at or below their reorder point (GET /reorder-rules/low-stock/). @param {Record<string, any>} [params] */
export function lowStock(params) {
	return reorderRules.collection('low-stock', params);
}
