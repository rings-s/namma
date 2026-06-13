<script>
  import { enhance } from '$app/forms';
  import { page } from '$app/stores';

  /** @type {{ form?: { error?: string; email?: string; password?: string } }} */
  let { form } = $props();
  let loading = $state(false);

  const email = $derived(form?.email ?? $page.url.searchParams.get('email') ?? '');
  const password = $derived(form?.password ?? $page.url.searchParams.get('password') ?? '');

  let otp = $state('');

  /** @param {Event} e */
  function onInput(e) {
    const target = /** @type {HTMLInputElement} */ (e.target);
    otp = target.value.replace(/\D/g, '').slice(0, 6);
    target.value = otp;
    if (otp.length === 6) {
      target.closest('form')?.requestSubmit();
    }
  }
</script>

<h2 class="text-xl font-semibold text-gray-900 mb-2">Two-factor authentication</h2>
<p class="text-sm text-gray-500 mb-6">Enter the 6-digit code from your authenticator app.</p>

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
  <input type="hidden" name="email" value={email} />
  <input type="hidden" name="password" value={password} />

  <div>
    <label for="otp_code" class="block text-sm font-medium text-gray-700 mb-1">Authentication code</label>
    <input
      id="otp_code"
      name="otp_code"
      type="text"
      inputmode="numeric"
      autocomplete="one-time-code"
      required
      maxlength="6"
      oninput={onInput}
      class="w-full rounded-lg border border-gray-300 px-3 py-3 text-center text-2xl tracking-[0.5em] font-mono focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
      placeholder="000000"
    />
  </div>

  <button
    type="submit"
    disabled={loading || otp.length < 6}
    class="w-full rounded-lg bg-gray-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50 transition-colors"
  >
    {loading ? 'Verifying…' : 'Verify'}
  </button>
</form>

<p class="mt-6 text-center text-sm text-gray-500">
  <a href="/login" class="font-medium text-gray-900 hover:underline">Back to login</a>
</p>
