import { i18n } from '$lib/i18n/i18n.svelte.js';

/**
 * Maps a domain enum value to a Badge colour variant. Values are unique enough
 * across the customer/marketing enums that one flat table is unambiguous.
 * @type {Record<string, string>}
 */
const VARIANT_BY_VALUE = {
	// generic / boolean-ish
	active: 'green',
	inactive: 'slate',
	draft: 'slate',
	// conversation / appointment workflow
	open: 'blue',
	assigned: 'amber',
	resolved: 'green',
	closed: 'slate',
	// campaign / dispatch / referral / recipient funnel
	scheduled: 'blue',
	sending: 'amber',
	sent: 'green',
	cancelled: 'slate',
	pending: 'amber',
	qualified: 'blue',
	rewarded: 'green',
	rejected: 'red',
	queued: 'amber',
	delivered: 'green',
	opened: 'green',
	clicked: 'green',
	read: 'green',
	failed: 'red',
	// segment types
	manual: 'slate',
	dynamic: 'blue',
	ai: 'violet',
	// AI recommendation priority + status
	low: 'slate',
	medium: 'blue',
	high: 'amber',
	critical: 'red',
	dismissed: 'slate',
	actioned: 'green',
	// package / sentiment / loyalty txn
	consumed: 'slate',
	expired: 'red',
	positive: 'green',
	neutral: 'slate',
	negative: 'red',
	earn: 'green',
	redeem: 'blue',
	adjust: 'amber',
	expire: 'red',
	// commerce / operations / finance workflow states
	completed: 'green',
	confirmed: 'blue',
	in_progress: 'amber',
	no_show: 'red',
	depleted: 'slate',
	issued: 'blue',
	partially_paid: 'amber',
	paid: 'green',
	overdue: 'red',
	void: 'slate',
	processed: 'green',
	partially_refunded: 'amber',
	// inventory + purchasing
	submitted: 'blue',
	partially_received: 'amber',
	received: 'green',
	// queue
	waiting: 'amber',
	called: 'blue',
	serving: 'amber',
	served: 'green',
	abandoned: 'slate',
	// commission entry types
	commission: 'green',
	bonus: 'blue',
	deduction: 'red',
	// goals
	achieved: 'green',
	missed: 'red'
};

/** @param {string} value */
export function statusVariant(value) {
	return VARIANT_BY_VALUE[value] ?? 'slate';
}

/** Title-case fallback for an enum value with no i18n entry. @param {string} value */
function humanize(value) {
	return value.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}

/**
 * Localized label for an enum value. Tries `enum.<group>.<value>` (for the rare
 * value whose label is context-specific), then the shared flat `enum.<value>`,
 * then a humanized fallback — so the UI never shows a bare key.
 * @param {string} group @param {string | null | undefined} value
 */
export function enumLabel(group, value) {
	if (!value) return '—';
	const scoped = `enum.${group}.${value}`;
	const scopedText = i18n.t(scoped);
	if (scopedText !== scoped) return scopedText;
	const flat = `enum.${value}`;
	const flatText = i18n.t(flat);
	return flatText === flat ? humanize(value) : flatText;
}
