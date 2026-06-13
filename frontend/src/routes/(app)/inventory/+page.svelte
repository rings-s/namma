<script>
  let { data } = $props();
  const products = $derived(data.products?.results ?? []);
  const lowStock = $derived(data.lowStock?.results ?? []);
</script>

<h1 class="text-2xl font-bold text-gray-900 mb-6">Inventory</h1>

{#if lowStock.length > 0}
  <div class="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-800">
    <strong>{lowStock.length} product{lowStock.length > 1 ? 's' : ''}</strong> below reorder point.
  </div>
{/if}

<div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
  <table class="min-w-full divide-y divide-gray-100 text-sm">
    <thead class="bg-gray-50">
      <tr>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Product</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">SKU</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Price</th>
        <th class="px-5 py-3 text-left font-medium text-gray-500">Status</th>
      </tr>
    </thead>
    <tbody class="divide-y divide-gray-100">
      {#each products as p}
        <tr class="hover:bg-gray-50">
          <td class="px-5 py-3 font-medium text-gray-900">{p.name}</td>
          <td class="px-5 py-3 text-gray-400 font-mono text-xs">{p.sku ?? '—'}</td>
          <td class="px-5 py-3 text-gray-700">{p.price ?? '—'}</td>
          <td class="px-5 py-3">
            <span class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium
                         {p.is_active ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'}">
              {p.is_active ? 'Active' : 'Inactive'}
            </span>
          </td>
        </tr>
      {/each}
      {#if products.length === 0}
        <tr><td colspan="4" class="px-5 py-6 text-center text-gray-400">No products found.</td></tr>
      {/if}
    </tbody>
  </table>
</div>
