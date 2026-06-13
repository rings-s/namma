<script>
  let { data } = $props();
  const campaigns = $derived(data.campaigns?.results ?? []);
  const promotions = $derived(data.promotions?.results ?? []);
</script>

<h1 class="text-2xl font-bold text-gray-900 mb-6">Marketing</h1>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <div class="bg-white rounded-xl border border-gray-200">
    <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
      <h2 class="font-medium text-gray-900">Campaigns</h2>
      <a href="/marketing/campaigns/new" class="text-sm text-gray-500 hover:text-gray-900">+ New</a>
    </div>
    <ul class="divide-y divide-gray-100 text-sm">
      {#each campaigns as c}
        <li class="px-5 py-3 flex items-center justify-between">
          <span class="text-gray-900">{c.name}</span>
          <span class="capitalize text-gray-400">{c.status}</span>
        </li>
      {/each}
      {#if campaigns.length === 0}
        <li class="px-5 py-4 text-gray-400">No campaigns.</li>
      {/if}
    </ul>
  </div>

  <div class="bg-white rounded-xl border border-gray-200">
    <div class="px-5 py-4 border-b border-gray-100">
      <h2 class="font-medium text-gray-900">Promotions</h2>
    </div>
    <ul class="divide-y divide-gray-100 text-sm">
      {#each promotions as p}
        <li class="px-5 py-3 flex items-center justify-between">
          <span class="text-gray-900">{p.name}</span>
          <span class="text-gray-400">{p.discount_type === 'percentage' ? `${p.discount_value}%` : `${p.discount_value} off`}</span>
        </li>
      {/each}
      {#if promotions.length === 0}
        <li class="px-5 py-4 text-gray-400">No promotions.</li>
      {/if}
    </ul>
  </div>
</div>
