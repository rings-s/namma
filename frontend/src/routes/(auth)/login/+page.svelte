<script>
  import { enhance } from '$app/forms';

  /** @type {{ form?: { error?: string } }} */
  let { form } = $props();
  let loading = $state(false);
</script>

<h2 class="text-xl font-semibold text-gray-900 mb-6">Sign in</h2>

{#if form?.error}
  <div class="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
    {form.error}
  </div>
{/if}

<form
  method="POST"
  use:enhance={() => {
    loading = true;
    return async ({ update }) => {
      loading = false;
      await update();
    };
  }}
  class="space-y-4"
>
  <div>
    <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Email</label>
    <input
      id="email"
      name="email"
      type="email"
      required
      autocomplete="email"
      class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
      placeholder="you@example.com"
    />
  </div>

  <div>
    <label for="password" class="block text-sm font-medium text-gray-700 mb-1">Password</label>
    <input
      id="password"
      name="password"
      type="password"
      required
      autocomplete="current-password"
      class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
      placeholder="••••••••"
    />
  </div>

  <button
    type="submit"
    disabled={loading}
    class="w-full rounded-lg bg-gray-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50 transition-colors"
  >
    {loading ? 'Signing in…' : 'Sign in'}
  </button>
</form>

<p class="mt-6 text-center text-sm text-gray-500">
  Don't have an account?
  <a href="/register" class="font-medium text-gray-900 hover:underline">Register</a>
</p>
