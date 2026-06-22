<script setup lang="ts">
const props = defineProps<{
  modelValue: string
  loading?: boolean
  placeholder?: string
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'submit'): void
}>()

const text = computed({
  get: () => props.modelValue,
  set: (v: string) => emit('update:modelValue', v),
})

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    emit('submit')
  }
}
</script>

<template>
  <div class="w-full max-w-2xl bg-white/90 backdrop-blur border border-royal-100 rounded-2xl shadow-soft px-4 pt-3 pb-2">
    <textarea
      v-model="text"
      rows="2"
      class="w-full resize-none bg-transparent outline-none text-sm text-gray-800 placeholder:text-gray-400"
      :placeholder="placeholder ?? '궁능 안내 챗봇에게 물어보기 (예: 경복궁 언제 지어졌어?)'"
      @keydown="onKeydown"
    />
    <div class="flex items-center justify-end mt-1">
      <button
        class="w-8 h-8 flex items-center justify-center rounded-full bg-royal-100 text-royal-500 hover:bg-royal-200 disabled:opacity-40"
        :disabled="loading || !text.trim()"
        title="전송"
        @click="emit('submit')"
      >
        <span v-if="!loading">↑</span>
        <span v-else class="animate-pulse">…</span>
      </button>
    </div>
  </div>
</template>
