import { resource } from './resource.js';

/** marketing app — campaigns, promotions, loyalty, referrals, lifecycle journeys. */

export const campaigns = resource('campaigns');
export const campaignRecipients = resource('campaign-recipients');
export const promotions = resource('promotions');
export const loyaltyPrograms = resource('loyalty-programs');
export const loyaltyTransactions = resource('loyalty-transactions');
export const referralPrograms = resource('referral-programs');
export const referrals = resource('referrals');
export const journeys = resource('journeys');
export const journeySteps = resource('journey-steps');

/** Send/launch a campaign to its consented audience (POST /campaigns/{id}/send/, marketer+). @param {string} id */
export function sendCampaign(id) {
	return campaigns.do(id, 'send');
}

/** Mark a referral as qualified, releasing rewards (POST /referrals/{id}/qualify/). @param {string} id @param {Record<string, any>} [body] */
export function qualifyReferral(id, body) {
	return referrals.do(id, 'qualify', body);
}
