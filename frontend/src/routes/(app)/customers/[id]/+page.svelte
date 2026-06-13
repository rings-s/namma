<script>
  let { data } = $props();
  const c = $derived(data.customer ?? {});
  const appointments = $derived(data.appointments?.results ?? []);
  const notes = $derived(data.notes?.results ?? []);
</script>

<div class="mb-6">
  <a href="/customers" class="text-sm text-gray-500 hover:text-gray-900">← Customers</a>
</div>

<div class="bg-white rounded-xl border border-gray-200 p-6 mb-6">
  <h1 class="text-2xl font-bold text-gray-900 mb-1">{c.first_name} {c.last_name}</h1>
  <p class="text-sm text-gray-500">{c.email ?? ''} · {c.phone ?? ''}</p>
  <div class="mt-4 grid grid-cols-3 gap-4 text-sm">
    <div><p class="text-gray-400">Visits</p><p class="font-medium">{c.visit_count ?? 0}</p></div>
    <div><p class="text-gray-400">Points</p><p class="font-medium">{c.loyalty_points ?? 0}</p></div>
    <div><p class="text-gray-400">Total spent</p><p class="font-medium">{c.total_spent ?? 0}</p></div>
  </div>
</div>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <div class="bg-white rounded-xl border border-gray-200">
    <div class="px-5 py-4 border-b border-gray-100 font-medium text-gray-900">Appointments</div>
    <ul class="divide-y divide-gray-100 text-sm">
      {#each appointments as a}
        <li class="px-5 py-3 flex justify-between">
          <span>{a.service_name ?? 'Service'}</span>
          <span class="text-gray-400">{a.scheduled_at ? new Date(a.scheduled_at).toLocaleDateString() : ''}</span>
          <span class="capitalize text-gray-500">{a.status}</span>
        </li>
      {/each}
      {#if appointments.length === 0}
        <li class="px-5 py-4 text-gray-400">No appointments.</li>
      {/if}
    </ul>
  </div>

  <div class="bg-white rounded-xl border border-gray-200">
    <div class="px-5 py-4 border-b border-gray-100 font-medium text-gray-900">Clinical Notes</div>
    <ul class="divide-y divide-gray-100 text-sm">
      {#each notes as n}
        <li class="px-5 py-3">
          <p class="text-gray-900">{n.note_type}</p>
          <p class="text-gray-400 text-xs mt-0.5">{n.created_at ? new Date(n.created_at).toLocaleDateString() : ''}</p>
        </li>
      {/each}
      {#if notes.length === 0}
        <li class="px-5 py-4 text-gray-400">No notes.</li>
      {/if}
    </ul>
  </div>
</div>
