import { resource } from './resource.js';

/**
 * integrations app — API keys, outbound webhooks, registered devices, and the
 * sync/outbox pipeline. Built last in the module sequence.
 */

export const apiKeys = resource('api-keys');
export const webhookEndpoints = resource('webhook-endpoints');
export const devices = resource('devices');
export const syncOperations = resource('sync-operations');
export const outboundEvents = resource('outbound-events');
export const webhookDeliveries = resource('webhook-deliveries');
export const integrationConnections = resource('integration-connections');

/** Re-attempt a failed/dead webhook delivery (POST /webhook-deliveries/{id}/replay/). @param {string} id */
export function replayDelivery(id) {
	return webhookDeliveries.do(id, 'replay');
}
