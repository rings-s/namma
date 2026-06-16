<script>
	import { i18n } from '$lib/i18n/i18n.svelte.js';
	import { auth } from '$lib/stores/auth.svelte.js';
	import { toasts } from '$lib/stores/toast.svelte.js';
	import { customerPreferences } from '$lib/api/customers.js';
	import { branches } from '$lib/api/organizations.js';
	import { employees } from '$lib/api/operations.js';
	import { errMessage, isAbortError } from '$lib/api/client.js';
	import { scopeToOrg } from '$lib/utils/scope.js';
	import DataState from '$lib/components/ui/DataState.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	/** @type {{ customer: any }} */
	let { customer } = $props();

	const CHANNELS = ['sms', 'email', 'whatsapp', 'push', 'in_app'];

	/** @type {any} */
	let pref = $state(null);
	/** @type {any[]} */
	let branchList = $state([]);
	/** @type {any[]} */
	let employeeList = $state([]);
	let loading = $state(true);
	let error = $state('');
	let saving = $state(false);

	// editable form fields
	let branch = $state('');
	let employee = $state('');
	let channel = $state('whatsapp');
	let marketingOptIn = $state(false);
	let reminderOptIn = $state(true);

	$effect(() => {
		const customerId = customer?.id;
		if (!customerId) return;
		const ctrl = new AbortController();
		load(customerId, ctrl.signal);
		return () => ctrl.abort();
	});

	/** @param {string} customerId @param {AbortSignal} [signal] */
	async function load(customerId, signal) {
		loading = true;
		error = '';
		try {
			const [prefs, brs, emps] = await Promise.all([
				customerPreferences.list(undefined, { signal }),
				branches.list(undefined, { signal }),
				employees.list(undefined, { signal })
			]);
			branchList = scopeToOrg(brs, auth.currentOrgId);
			employeeList = scopeToOrg(emps, auth.currentOrgId);
			pref = prefs.find((/** @type {any} */ p) => p.customer === customerId) ?? null;
			if (pref) {
				branch = pref.preferred_branch ?? '';
				employee = pref.preferred_employee ?? '';
				channel = pref.communication_channel;
				marketingOptIn = pref.marketing_opt_in;
				reminderOptIn = pref.reminder_opt_in;
			}
		} catch (err) {
			if (isAbortError(err)) return;
			error = errMessage(err) || i18n.t('common.error');
		} finally {
			if (!signal?.aborted) loading = false;
		}
	}

	/** @param {SubmitEvent} event */
	async function save(event) {
		event.preventDefault();
		saving = true;
		const body = {
			customer: customer.id,
			preferred_branch: branch || null,
			preferred_employee: employee || null,
			communication_channel: channel,
			marketing_opt_in: marketingOptIn,
			reminder_opt_in: reminderOptIn
		};
		try {
			pref = pref
				? await customerPreferences.patch(pref.id, body)
				: await customerPreferences.create(body);
			toasts.success(i18n.t('common.saved'));
		} catch (err) {
			toasts.error(errMessage(err) || i18n.t('common.error'));
		} finally {
			saving = false;
		}
	}

	/** @param {any} e */
	function empName(e) {
		return e.display_name || e.name || `${e.first_name ?? ''} ${e.last_name ?? ''}`.trim() || e.id;
	}
</script>

<DataState {loading} {error} onRetry={() => load(customer.id)}>
	<form
		onsubmit={save}
		class="max-w-lg space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
	>
		<div>
			<label for="pf-channel" class="mb-1 block text-sm font-medium text-slate-700">
				{i18n.t('prefs.channel')}
			</label>
			<select
				id="pf-channel"
				bind:value={channel}
				class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
			>
				{#each CHANNELS as c (c)}<option value={c}>{i18n.t(`enum.${c}`)}</option>{/each}
			</select>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label for="pf-branch" class="mb-1 block text-sm font-medium text-slate-700">
					{i18n.t('prefs.branch')}
				</label>
				<select
					id="pf-branch"
					bind:value={branch}
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				>
					<option value="">{i18n.t('common.none')}</option>
					{#each branchList as b (b.id)}<option value={b.id}>{b.name}</option>{/each}
				</select>
			</div>
			<div>
				<label for="pf-emp" class="mb-1 block text-sm font-medium text-slate-700"
					>{i18n.t('prefs.employee')}</label
				>
				<select
					id="pf-emp"
					bind:value={employee}
					class="w-full rounded-lg border-slate-300 text-sm focus:border-brand-500 focus:ring-brand-500"
				>
					<option value="">{i18n.t('common.none')}</option>
					{#each employeeList as e (e.id)}<option value={e.id}>{empName(e)}</option>{/each}
				</select>
			</div>
		</div>
		<label class="flex items-center gap-3 text-sm text-slate-700">
			<input
				type="checkbox"
				bind:checked={marketingOptIn}
				class="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
			/>
			{i18n.t('prefs.marketingOptIn')}
		</label>
		<label class="flex items-center gap-3 text-sm text-slate-700">
			<input
				type="checkbox"
				bind:checked={reminderOptIn}
				class="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
			/>
			{i18n.t('prefs.reminderOptIn')}
		</label>
		<button
			type="submit"
			disabled={saving}
			class="flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
		>
			{#if saving}<Spinner size={16} />{/if}
			{pref ? i18n.t('common.save') : i18n.t('prefs.create')}
		</button>
	</form>
</DataState>
