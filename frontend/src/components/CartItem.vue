<script setup lang="ts">
import { computed } from "vue"
import { useCartStore } from "@/stores/cart"
import type { Plugin } from "@/types/marketplace"

interface Props {
  plugin: Plugin
}
const props = defineProps<Props>()

const cartStore = useCartStore()

const displayName = computed(() =>
  props.plugin.label.zh_Hans || props.plugin.label.en_US
)

function remove(): void {
  cartStore.removeItem(props.plugin.plugin_id)
}
</script>

<template>
  <div class="flex gap-3 p-3 rounded-lg border border-gray-200 bg-gray-50">
    <div class="flex-1 min-w-0">
      <div class="flex items-center justify-between">
        <h3
          data-testid="plugin-name"
          class="text-sm font-medium text-gray-900 truncate"
        >
          {{ displayName }}
        </h3>
        <button
          data-testid="remove-item-btn"
          class="shrink-0 p-1 text-gray-400 hover:text-red-500"
          @click="remove"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>
      <p class="text-xs text-gray-500 mt-0.5">
        {{ plugin.org }} · {{ plugin.latest_version }}
      </p>
      <span
        v-if="plugin.category"
        data-testid="category-tag"
        class="inline-block mt-1 px-1.5 py-0.5 text-xs rounded bg-blue-100 text-blue-700"
      >
        {{ plugin.category }}
      </span>
    </div>
  </div>
</template>
