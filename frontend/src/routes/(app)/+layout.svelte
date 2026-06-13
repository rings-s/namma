<script>
  import { page } from '$app/stores';

  let { children, data } = $props();

  const nav = [
    { href: '/dashboard',   label: 'Dashboard' },
    { href: '/customers',   label: 'Customers' },
    { href: '/appointments',label: 'Appointments' },
    { href: '/employees',   label: 'Employees' },
    { href: '/sales',       label: 'Sales' },
    { href: '/inventory',   label: 'Inventory' },
    { href: '/marketing',   label: 'Marketing' },
    { href: '/analytics',   label: 'Analytics' },
    { href: '/settings',    label: 'Settings' },
  ];

  const email = $derived(
    typeof data.user?.email === 'string' ? data.user.email : ''
  );
</script>

<div class="flex h-screen bg-gray-50">
  <!-- Sidebar -->
  <aside class="w-56 bg-white border-r border-gray-200 flex flex-col shrink-0">
    <div class="px-5 py-5 border-b border-gray-100">
      <span class="text-xl font-bold text-gray-900">نماء</span>
    </div>

    <nav class="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
      {#each nav as item}
        {@const active = $page.url.pathname.startsWith(item.href)}
        <a
          href={item.href}
          class="flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors
                 {active ? 'bg-gray-900 text-white' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'}"
        >
          {item.label}
        </a>
      {/each}
    </nav>

    <div class="px-4 py-4 border-t border-gray-100">
      <p class="text-xs text-gray-500 truncate mb-2">{email}</p>
      <form method="POST" action="/logout">
        <button
          type="submit"
          class="w-full text-left text-sm text-gray-500 hover:text-gray-900 transition-colors"
        >
          Sign out
        </button>
      </form>
    </div>
  </aside>

  <!-- Main content -->
  <div class="flex-1 flex flex-col overflow-hidden">
    <main class="flex-1 overflow-y-auto p-6">
      {@render children()}
    </main>
  </div>
</div>
