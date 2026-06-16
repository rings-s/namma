/**
 * Sidebar navigation, grouped to mirror the module map. Modules whose
 * frontend isn't built yet are flagged `comingSoon` so the shell can render
 * them disabled rather than linking to dead routes. `minRole` gates sensitive
 * areas against the user's role in the current org.
 *
 * @typedef {{ key: string; href: string; labelKey: string; icon: string;
 *   comingSoon?: boolean; minRole?: string }} NavItem
 * @typedef {{ key: string; labelKey: string; items: NavItem[] }} NavGroup
 */

/** @type {NavGroup[]} */
export const NAV = [
	{
		key: 'workspace',
		labelKey: 'nav.section.workspace',
		items: [
			{ key: 'dashboard', href: '/dashboard', labelKey: 'nav.dashboard', icon: 'grid' },
			{ key: 'calendar', href: '/calendar', labelKey: 'nav.calendar', icon: 'calendar' },
			{ key: 'commerce', href: '/commerce', labelKey: 'nav.commerce', icon: 'cart' },
			{
				key: 'finance',
				href: '/finance',
				labelKey: 'nav.finance',
				icon: 'receipt',
				minRole: 'accountant'
			},
			{ key: 'staff', href: '/staff', labelKey: 'nav.staff', icon: 'badge', minRole: 'manager' },
			{ key: 'inventory', href: '/inventory', labelKey: 'nav.inventory', icon: 'box' },
			{ key: 'analytics', href: '/analytics', labelKey: 'nav.analytics', icon: 'chart' },
			{ key: 'ai', href: '/ai', labelKey: 'nav.ai', icon: 'sparkles' }
		]
	},
	{
		key: 'customers',
		labelKey: 'nav.section.customers',
		items: [
			{ key: 'customers', href: '/customers', labelKey: 'nav.customers', icon: 'users' },
			{ key: 'segments', href: '/customers/segments', labelKey: 'nav.segments', icon: 'tag' },
			{ key: 'surveys', href: '/customers/surveys', labelKey: 'nav.surveys', icon: 'star' },
			{
				key: 'conversations',
				href: '/customers/conversations',
				labelKey: 'nav.conversations',
				icon: 'chat'
			}
		]
	},
	{
		key: 'marketing',
		labelKey: 'nav.section.marketing',
		items: [
			{
				key: 'campaigns',
				href: '/marketing/campaigns',
				labelKey: 'nav.campaigns',
				icon: 'megaphone'
			},
			{ key: 'journeys', href: '/marketing/journeys', labelKey: 'nav.journeys', icon: 'send' },
			{ key: 'loyalty', href: '/marketing/loyalty', labelKey: 'nav.loyalty', icon: 'heart' },
			{ key: 'referrals', href: '/marketing/referrals', labelKey: 'nav.referrals', icon: 'gift' }
		]
	},
	{
		key: 'account',
		labelKey: 'nav.section.account',
		items: [
			{
				key: 'settings',
				href: '/settings',
				labelKey: 'nav.settings',
				icon: 'cog',
				minRole: 'admin'
			},
			{ key: 'profile', href: '/profile', labelKey: 'nav.profile', icon: 'user' },
			{ key: 'security', href: '/security', labelKey: 'nav.security', icon: 'shield' }
		]
	}
];
