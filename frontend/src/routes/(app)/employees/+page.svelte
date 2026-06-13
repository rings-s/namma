<script>
  let { data } = $props();
  const employees = $derived(data.employees?.results ?? []);
</script>

<h1 class="text-2xl font-bold text-gray-900 mb-6">Employees</h1>

<div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
  <table class="min-w-full divide-y divide-gray-100 text-sm">
    <thead class="bg-gray-50">
      <tr>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Name</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Role</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Branch</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Status</th>
      </tr>
    </thead>
    <tbody class="divide-y divide-gray-100">
      {#each employees as e}
        <tr class="hover:bg-gray-50">
          <td class="px-5 py-3 font-medium text-gray-900">{e.first_name ?? ''} {e.last_name ?? ''}</td>
          <td class="px-5 py-3 text-gray-500 capitalize">{e.role ?? '—'}</td>
          <td class="px-5 py-3 text-gray-500">{e.branch_name ?? e.branch ?? '—'}</td>
          <td class="px-5 py-3">
            <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium
                         {e.is_active ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'}">
              {e.is_active ? 'Active' : 'Inactive'}
            </span>
          </td>
        </tr>
      {/each}
      {#if employees.length === 0}
        <tr><td colspan="4" class="px-5 py-6 text-center text-gray-400">No employees found.</td></tr>
      {/if}
    </tbody>
  </table>
</div>
