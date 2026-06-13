export { createClient } from './client.js';
export { accountsApi } from './accounts.js';
export { organizationsApi } from './organizations.js';
export { customersApi } from './customers.js';
export { commerceApi } from './commerce.js';
export { operationsApi } from './operations.js';
export { financialsApi } from './financials.js';
export { communicationsApi } from './communications.js';
export { marketingApi } from './marketing.js';
export { analyticsApi } from './analytics.js';
export { aiApi } from './ai.js';
export { integrationsApi } from './integrations.js';
export { inventoryApi } from './inventory.js';
export { coreApi } from './core.js';

import { createClient } from './client.js';
import { accountsApi } from './accounts.js';
import { organizationsApi } from './organizations.js';
import { customersApi } from './customers.js';
import { commerceApi } from './commerce.js';
import { operationsApi } from './operations.js';
import { financialsApi } from './financials.js';
import { communicationsApi } from './communications.js';
import { marketingApi } from './marketing.js';
import { analyticsApi } from './analytics.js';
import { aiApi } from './ai.js';
import { integrationsApi } from './integrations.js';
import { inventoryApi } from './inventory.js';
import { coreApi } from './core.js';

/**
 * Build a fully-wired API bundle from a base URL, token getter, and fetch implementation.
 * Use this in server load functions and hooks.
 *
 * @param {string} baseUrl
 * @param {() => string | null} getToken
 * @param {typeof fetch} fetchFn
 */
export function createApi(baseUrl, getToken, fetchFn) {
  const client = createClient(baseUrl, getToken, fetchFn);
  return {
    accounts: accountsApi(client),
    organizations: organizationsApi(client),
    customers: customersApi(client),
    commerce: commerceApi(client),
    operations: operationsApi(client),
    financials: financialsApi(client),
    communications: communicationsApi(client),
    marketing: marketingApi(client),
    analytics: analyticsApi(client),
    ai: aiApi(client),
    integrations: integrationsApi(client),
    inventory: inventoryApi(client),
    core: coreApi(client),
  };
}
