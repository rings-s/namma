import { resource } from './resource.js';

/** commerce app — catalog, sales/POS, stored value (gift cards, store credit, packages), pricing. */

export const serviceCategories = resource('service-categories');
export const services = resource('services');
export const products = resource('products');
export const sales = resource('sales');
export const saleItems = resource('sale-items');
export const giftCards = resource('gift-cards');
export const giftCardTransactions = resource('gift-card-transactions');
export const storeCreditAccounts = resource('store-credit-accounts');
export const storeCreditTransactions = resource('store-credit-transactions');
export const packages = resource('packages');
export const packageItems = resource('package-items');
export const customerPackages = resource('customer-packages');
export const packageRedemptions = resource('package-redemptions');
export const pricingRules = resource('pricing-rules');

/** Commission breakdown for a sale (GET /sales/{id}/commissions/). @param {string} id */
export function saleCommissions(id) {
	return sales.read(id, 'commissions');
}

/** Redeem against a gift card (POST /gift-cards/{id}/redeem/). @param {string} id @param {Record<string, any>} [body] */
export function redeemGiftCard(id, body) {
	return giftCards.do(id, 'redeem', body);
}

/** Adjust a store-credit balance (POST /store-credit-accounts/{id}/adjust/, manager+). @param {string} id @param {Record<string, any>} [body] */
export function adjustStoreCredit(id, body) {
	return storeCreditAccounts.do(id, 'adjust', body);
}

/** Redeem a session from a customer package (POST /customer-packages/{id}/redeem/). @param {string} id @param {Record<string, any>} [body] */
export function redeemPackage(id, body) {
	return customerPackages.do(id, 'redeem', body);
}

/** Resolve the single winning price for a line (POST /pricing-rules/quote/). Never stacks rules. @param {Record<string, any>} [body] */
export function priceQuote(body) {
	return pricingRules.collectionDo('quote', body);
}
