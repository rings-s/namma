<script>
  let { data } = $props();
  const goals = $derived(data.goals?.results ?? []);
  const leaderboard = $derived(data.leaderboard?.results ?? []);
</script>

<h1 class="text-2xl font-bold text-gray-900 mb-6">Analytics</h1>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <div class="bg-white rounded-xl border border-gray-200">
    <div class="px-5 py-4 border-b border-gray-100">
      <h2 class="font-medium text-gray-900">Goals</h2>
    </div>
    <ul class="divide-y divide-gray-100 text-sm">
      {#each goals as g}
        <li class="px-5 py-3">
          <div class="flex items-center justify-between mb-1">
            <span class="text-gray-900">{g.name}</span>
            <span class="text-gray-400">{g.progress_percent ?? 0}%</span>
          </div>
          <div class="w-full bg-gray-100 rounded-full h-1.5">
            <div class="bg-gray-900 h-1.5 rounded-full" style="width: {Math.min(g.progress_percent ?? 0, 100)}%"></div>
          </div>
        </li>
      {/each}
      {#if goals.length === 0}
        <li class="px-5 py-4 text-gray-400">No goals set.</li>
      {/if}
    </ul>
  </div>

  <div class="bg-white rounded-xl border border-gray-200">
    <div class="px-5 py-4 border-b border-gray-100">
      <h2 class="font-medium text-gray-900">Employee Leaderboard</h2>
    </div>
    <ul class="divide-y divide-gray-100 text-sm">
      {#each leaderboard as e, i}
        <li class="px-5 py-3 flex items-center gap-3">
          <span class="text-gray-300 font-mono text-xs w-5">{i + 1}</span>
          <span class="flex-1 text-gray-900">{e.employee_name ?? e.employee ?? '—'}</span>
          <span class="text-gray-500">{e.total_revenue ?? 0}</span>
        </li>
      {/each}
      {#if leaderboard.length === 0}
        <li class="px-5 py-4 text-gray-400">No data.</li>
      {/if}
    </ul>
  </div>
</div>
