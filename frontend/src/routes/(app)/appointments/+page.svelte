<script>
  let { data } = $props();
  const appointments = $derived(data.appointments?.results ?? []);
</script>

<h1 class="text-2xl font-bold text-gray-900 mb-6">Appointments</h1>

<div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
  <table class="min-w-full divide-y divide-gray-100 text-sm">
    <thead class="bg-gray-50">
      <tr>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Customer</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Service</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Date &amp; Time</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Employee</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Status</th>
      </tr>
    </thead>
    <tbody class="divide-y divide-gray-100">
      {#each appointments as a}
        <tr class="hover:bg-gray-50">
          <td class="px-5 py-3 text-gray-900">{a.customer_name ?? a.customer ?? '—'}</td>
          <td class="px-5 py-3 text-gray-500">{a.service_name ?? a.service ?? '—'}</td>
          <td class="px-5 py-3 text-gray-500">
            {a.scheduled_at ? new Date(a.scheduled_at).toLocaleString() : '—'}
          </td>
          <td class="px-5 py-3 text-gray-500">{a.employee_name ?? a.employee ?? '—'}</td>
          <td class="px-5 py-3 capitalize text-gray-500">{a.status ?? '—'}</td>
        </tr>
      {/each}
      {#if appointments.length === 0}
        <tr><td colspan="5" class="px-5 py-6 text-center text-gray-400">No appointments found.</td></tr>
      {/if}
    </tbody>
  </table>
</div>
