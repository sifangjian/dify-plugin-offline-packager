<template>
  <div class="bg-white rounded-lg border p-4 hover:shadow-md transition-shadow">
    <div class="flex items-start gap-3">
      <img
        :src="plugin.icon || '/default-icon.svg'"
        class="w-10 h-10 rounded"
        :alt="getI18nText(plugin.label)"
      >
      <div class="min-w-0 flex-1">
        <h3 class="font-medium truncate">
          {{ getI18nText(plugin.label) }}
        </h3>
        <p class="text-sm text-gray-500 truncate">
          {{ plugin.org }}
        </p>
      </div>
    </div>
    <p class="mt-2 text-sm text-gray-600 line-clamp-2">
      {{ getI18nText(plugin.brief) }}
    </p>
    <div class="mt-3 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span class="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded">
          {{ plugin.category }}
        </span>
        <span class="text-xs text-gray-400">
          {{ formatInstallCount(plugin.install_count) }} 次安装
        </span>
      </div>
      <button
        :disabled="cartStore.hasItem(plugin.plugin_id)"
        :class="cartStore.hasItem(plugin.plugin_id)
          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
          : 'bg-blue-500 text-white hover:bg-blue-600'"
        class="px-3 py-1 text-sm rounded-lg transition-colors"
        @click="cartStore.addItem(plugin)"
      >
        {{ cartStore.hasItem(plugin.plugin_id) ? '已添加' : '添加' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Plugin } from "@/types/marketplace"
import { useCartStore } from "@/stores/cart"

const cartStore = useCartStore()

interface Props {
  plugin: Plugin
}
defineProps<Props>()

function getI18nText(text: { zh_Hans: string; en_US: string }): string {
  return text.zh_Hans || text.en_US
}

function formatInstallCount(count: number): string {
  if (count >= 10000) return `${(count / 10000).toFixed(1)}万`
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`
  return String(count)
}
</script>
