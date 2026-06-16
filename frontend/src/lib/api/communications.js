import { resource } from './resource.js';

/**
 * communications app — message templates & dispatches, consent ledger, email
 * delivery events, in-app notifications, and the two-way conversation inbox.
 */

export const messageTemplates = resource('message-templates');
export const messageDispatches = resource('message-dispatches');
export const consentRecords = resource('consent-records');
export const emailEvents = resource('email-events');
export const notifications = resource('notifications');
export const notificationTemplates = resource('notification-templates');
export const conversations = resource('conversations');
export const conversationMessages = resource('conversation-messages');

/**
 * Queue a dispatch for sending via its channel gateway (POST /message-dispatches/{id}/send/).
 * Create the dispatch as `queued` first, then call this.
 * @param {string} id
 */
export function sendDispatch(id) {
	return messageDispatches.do(id, 'send');
}

/** Assign a conversation to an agent (POST /conversations/{id}/assign/). @param {string} id @param {Record<string, any>} [body] */
export function assignConversation(id, body) {
	return conversations.do(id, 'assign', body);
}

/** Mark a conversation resolved (POST /conversations/{id}/resolve/). @param {string} id */
export function resolveConversation(id) {
	return conversations.do(id, 'resolve');
}

/** Close a conversation (POST /conversations/{id}/close/). @param {string} id */
export function closeConversation(id) {
	return conversations.do(id, 'close');
}
