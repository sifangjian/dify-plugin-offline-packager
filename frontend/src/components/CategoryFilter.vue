<template>
  <div class="flex gap-2 overflow-x-auto pb-1">
    <button
      v-for="cat in CATEGORIES"
      :key="cat.value"
      @click="emit('update:category', cat.value)"
      :class="category === cat.value
        ? 'bg-blue-500 text-white'
        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
      class="px-3 py-1.5 text-sm rounded-full whitespace-nowrap shrink-0"
    >
      {{ cat.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
interface Props {
  category: string
}
defineProps<Props>()

const emit = defineEmits<{
  "update:category": [value: string]
}>()

const CATEGORIES = [
  { value: "", label: "全部" },
  { value: "model", label: "Model" },
  { value: "tool", label: "Tool" },
  { value: "agent-strategy", label: "Agent Strategy" },
  { value: "extension", label: "Extension" },
  { value: "bundle", label: "Bundle" },
] as const
</script>
