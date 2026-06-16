import { i18n } from '$lib/i18n/i18n.svelte.js';

/**
 * Format an amount as currency in the active locale.
 * @param {number | string} amount
 * @param {string} [currency]
 */
export function money(amount, currency = 'SAR') {
	const value = typeof amount === 'string' ? Number(amount) : amount;
	return new Intl.NumberFormat(i18n.locale === 'ar' ? 'ar-SA' : 'en-US', {
		style: 'currency',
		currency,
		maximumFractionDigits: 2
	}).format(Number.isFinite(value) ? value : 0);
}

/** @param {number | string} value */
export function number(value) {
	const n = typeof value === 'string' ? Number(value) : value;
	return new Intl.NumberFormat(i18n.locale === 'ar' ? 'ar-SA' : 'en-US').format(
		Number.isFinite(n) ? n : 0
	);
}

/** @param {string | null | undefined} iso */
export function dateTime(iso) {
	if (!iso) return '—';
	return new Intl.DateTimeFormat(i18n.locale === 'ar' ? 'ar-SA' : 'en-US', {
		dateStyle: 'medium',
		timeStyle: 'short'
	}).format(new Date(iso));
}

/** @param {string | null | undefined} iso */
export function date(iso) {
	if (!iso) return '—';
	return new Intl.DateTimeFormat(i18n.locale === 'ar' ? 'ar-SA' : 'en-US', {
		dateStyle: 'medium'
	}).format(new Date(iso));
}
