<script>
  let { data } = $props();
  const org = $derived(data.organizations?.results?.[0] ?? {});
  const branches = $derived(data.branches?.results ?? []);
</script>

<h1 class="text-2xl font-bold text-gray-900 mb-6">Settings</h1>

<div class="space-y-6 max-w-2xl">
  <div class="bg-white rounded-xl border border-gray-200 p-6">
    <h2 class="font-medium text-gray-900 mb-4">Organization</h2>
    <dl class="space-y-3 text-sm">
      <div class="flex justify-between">
        <dt class="text-gray-500">Name</dt>
        <dd class="text-gray-900">{org.name ?? '—'}</dd>
      </div>
      <div class="flex justify-between">
        <dt class="text-gray-500">VAT number</dt>
        <dd class="text-gray-900">{org.vat_number ?? '—'}</dd>
      </div>
      <div class="flex justify-between">
        <dt class="text-gray-500">CR number</dt>
        <dd class="text-gray-900">{org.commercial_registration_number ?? '—'}</dd>
      </div>
      <div class="flex justify-between">
        <dt class="text-gray-500">Tier</dt>
        <dd class="text-gray-900 capitalize">{org.tenant_tier ?? '—'}</dd>
      </div>
    </dl>
  </div>

  <div class="bg-white rounded-xl border border-gray-200">
    <div class="px-5 py-4 border-b border-gray-100">
      <h2 class="font-medium text-gray-900">Branches ({branches.length})</h2>
    </div>
    <ul class="divide-y divide-gray-100 text-sm">
      {#each branches as b}
        <li class="px-5 py-3 flex items-center justify-between">
          <span class="text-gray-900">{b.name}</span>
          <span class="text-gray-400">{b.city ?? ''}</span>
        </li>
      {/each}
      {#if branches.length === 0}
        <li class="px-5 py-4 text-gray-400">No branches configured.</li>
      {/if}
    </ul>
  </div>
</div>
