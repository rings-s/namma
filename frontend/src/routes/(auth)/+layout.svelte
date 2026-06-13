<script>
  let { children } = $props();
</script>

<div class="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4">
  <div class="w-full max-w-md">
    <div class="text-center mb-8">
      <h1 class="text-4xl font-bold text-gray-900">نماء</h1>
      <p class="mt-2 text-sm text-gray-500">Business Management Platform</p>
    </div>
    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
      {@render children()}
    </div>
  </div>
</div>
