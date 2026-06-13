<script>
  let { data } = $props();
  const sales = $derived(data.sales?.results ?? []);
</script>

<h1 class="text-2xl font-bold text-gray-900 mb-6">Sales</h1>

<div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
  <table class="min-w-full divide-y divide-gray-100 text-sm">
    <thead class="bg-gray-50">
      <tr>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Customer</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Total</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Status</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Date</th>
      </tr>
    </thead>
    <tbody class="divide-y divide-gray-100">
      {#each sales as s}
        <tr class="hover:bg-gray-50">
          <td class="px-5 py-3 text-gray-900">{s.customer_name ?? s.customer ?? '—'}</td>
          <td class="px-5 py-3 text-gray-900 font-medium">{s.total_amount ?? '—'}</td>
          <td class="px-5 py-3 capitalize text-gray-500">{s.status ?? '—'}</td>
          <td class="px-5 py-3 text-gray-400">
            {s.created_at ? new Date(s.created_at).toLocaleDateString() : '—'}
          </td>
        </tr>
      {/each}
      {#if sales.length === 0}
        <tr><td colspan="4" class="px-5 py-6 text-center text-gray-400">No sales found.</td></tr>
      {/if}
    </tbody>
  </table>
</div>
