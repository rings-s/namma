<script>
  import { enhance } from '$app/forms';
  import { page } from '$app/stores';

  /** @type {{ form?: { error?: string } }} */
  let { form } = $props();
  let loading = $state(false);
  let registered = $derived($page.url.searchParams.get('registered') === '1');
</script>

<h2 class="text-xl font-semibold text-gray-900 mb-6">Create account</h2>

{#if registered}
  <div class="mb-4 rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
    Account created — please sign in.
  </div>
{/if}

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
  <div class="grid grid-cols-2 gap-3">
    <div>
      <label for="first_name" class="block text-sm font-medium text-gray-700 mb-1">First name</label>
      <input
        id="first_name"
        name="first_name"
        type="text"
        required
        class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
      />
    </div>
    <div>
      <label for="last_name" class="block text-sm font-medium text-gray-700 mb-1">Last name</label>
      <input
        id="last_name"
        name="last_name"
        type="text"
        required
        class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
      />
    </div>
  </div>

  <div>
    <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Email</label>
    <input
      id="email"
      name="email"
      type="email"
      required
      autocomplete="email"
      class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
    />
  </div>

  <div>
    <label for="phone" class="block text-sm font-medium text-gray-700 mb-1">Phone</label>
    <input
      id="phone"
      name="phone"
      type="tel"
      class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
      placeholder="+966 5x xxx xxxx"
    />
  </div>

  <div>
    <label for="password" class="block text-sm font-medium text-gray-700 mb-1">Password</label>
    <input
      id="password"
      name="password"
      type="password"
      required
      autocomplete="new-password"
      class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
    />
  </div>

  <button
    type="submit"
    disabled={loading}
    class="w-full rounded-lg bg-gray-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50 transition-colors"
  >
    {loading ? 'Creating account…' : 'Create account'}
  </button>
</form>

<p class="mt-6 text-center text-sm text-gray-500">
  Already have an account?
  <a href="/login" class="font-medium text-gray-900 hover:underline">Sign in</a>
</p>
