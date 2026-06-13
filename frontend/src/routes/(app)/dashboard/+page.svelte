<script>
  let { data } = $props();
  const appointments = $derived(data.appointments?.results ?? []);
</script>

<h1 class="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

<div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
  {#each [
    { label: 'Appointments today', value: data.metrics?.results?.[0]?.total_appointments ?? '—' },
    { label: 'Revenue today',      value: data.metrics?.results?.[0]?.total_revenue ?? '—' },
    { label: 'New customers',      value: data.metrics?.results?.[0]?.new_customers ?? '—' },
  ] as stat}
    <div class="bg-white rounded-xl border border-gray-200 p-5">
      <p class="text-sm text-gray-500">{stat.label}</p>
      <p class="mt-1 text-2xl font-semibold text-gray-900">{stat.value}</p>
    </div>
  {/each}
</div>

<div class="bg-white rounded-xl border border-gray-200">
  <div class="px-5 py-4 border-b border-gray-100">
    <h2 class="text-base font-medium text-gray-900">Recent appointments</h2>
  </div>
  {#if appointments.length === 0}
    <p class="px-5 py-6 text-sm text-gray-400">No appointments yet.</p>
  {:else}
    <ul class="divide-y divide-gray-100">
      {#each appointments as appt}
        <li class="px-5 py-3 flex items-center justify-between text-sm">
          <span class="text-gray-900">{appt.customer_name ?? appt.customer ?? 'Customer'}</span>
          <span class="text-gray-500">{appt.scheduled_at ? new Date(appt.scheduled_at).toLocaleString() : ''}</span>
          <span class="text-gray-400 capitalize">{appt.status ?? ''}</span>
        </li>
      {/each}
    </ul>
  {/if}
</div>
