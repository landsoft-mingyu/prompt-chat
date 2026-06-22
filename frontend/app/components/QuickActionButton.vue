<script setup lang="ts">
defineProps<{
  icon: string
  label: string
}>()
</script>

<template>
  <button
    class="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-royal-200 bg-white/80 hover:bg-royal-50 text-sm text-gray-700 shadow-sm transition"
  >
    <span class="text-royal-400">{{ icon }}</span>
    <span>{{ label }}</span>
  </button>
</template>
