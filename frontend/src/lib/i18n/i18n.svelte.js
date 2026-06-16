import { browser } from '$app/environment';
import { STORAGE_KEYS } from '$lib/config.js';
import { LOCALE_META, LOCALES, messages } from './dict.js';

/**
 * Runes-based i18n store. Holds the active locale, exposes the text direction,
 * and resolves keys through `t()` with optional `{placeholder}` interpolation.
 * Mirrors the document `lang`/`dir` so the whole app flips RTL/LTR.
 */
function createI18n() {
	let locale = $state(resolveInitialLocale());

	const dir = $derived(LOCALE_META[locale].dir);

	/**
	 * @param {string} key
	 * @param {Record<string, string | number>} [params]
	 */
	function t(key, params) {
		const entry = messages[key];
		let value = entry ? (entry[locale] ?? entry.en) : key;
		if (params) {
			for (const [name, replacement] of Object.entries(params)) {
				value = value.replaceAll(`{${name}}`, String(replacement));
			}
		}
		return value;
	}

	/** @param {import('./dict.js').Locale} next */
	function setLocale(next) {
		if (!LOCALES.includes(next)) return;
		locale = next;
		if (browser) {
			localStorage.setItem(STORAGE_KEYS.locale, next);
			syncDocument();
		}
	}

	function toggle() {
		setLocale(locale === 'ar' ? 'en' : 'ar');
	}

	function syncDocument() {
		if (!browser) return;
		document.documentElement.lang = locale;
		document.documentElement.dir = LOCALE_META[locale].dir;
	}

	return {
		get locale() {
			return locale;
		},
		get dir() {
			return dir;
		},
		t,
		setLocale,
		toggle,
		syncDocument
	};
}

/** @returns {import('./dict.js').Locale} */
function resolveInitialLocale() {
	if (!browser) return 'en';
	const stored = localStorage.getItem(STORAGE_KEYS.locale);
	if (stored === 'ar' || stored === 'en') return stored;
	return navigator.language?.startsWith('ar') ? 'ar' : 'en';
}

export const i18n = createI18n();
