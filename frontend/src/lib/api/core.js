import { resource } from './resource.js';

/**
 * core app — shared reference data (countries, currencies, translations) and
 * the audit/access log trails. Reference lists are read-mostly; logs are
 * read-only.
 */

export const countries = resource('countries');
export const currencies = resource('currencies');
export const translations = resource('translations');
export const auditLogs = resource('audit-logs');
export const accessLogs = resource('access-logs');
