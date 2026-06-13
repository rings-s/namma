<script>
  let { data } = $props();
  const customers = $derived(data.customers?.results ?? []);
</script>

<div class="flex items-center justify-between mb-6">
  <h1 class="text-2xl font-bold text-gray-900">Customers</h1>
  <a href="/customers/new" class="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700">
    Add customer
  </a>
</div>

<div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
  <table class="min-w-full divide-y divide-gray-100 text-sm">
    <thead class="bg-gray-50">
      <tr>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Name</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Phone</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Visits</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Last visit</th>
      </tr>
    </thead>
    <tbody class="divide-y divide-gray-100">
      {#each customers as c}
        <tr class="hover:bg-gray-50">
          <td class="px-5 py-3">
            <a href="/customers/{c.id}" class="font-medium text-gray-900 hover:underline">
              {c.first_name} {c.last_name}
            </a>
          </td>
          <td class="px-5 py-3 text-gray-500">{c.phone ?? '—'}</td>
          <td class="px-5 py-3 text-gray-500">{c.visit_count ?? 0}</td>
          <td class="px-5 py-3 text-gray-500">
            {c.last_visit_at ? new Date(c.last_visit_at).toLocaleDateString() : '—'}
          </td>
        </tr>
      {/each}
      {#if customers.length === 0}
        <tr><td colspan="4" class="px-5 py-6 text-center text-gray-400">No customers found.</td></tr>
      {/if}
    </tbody>
  </table>
</div>
