import { defineStore } from "pinia"
import { ref, computed } from "vue"
import type { Plugin } from "@/types/marketplace"
import type { CartItem } from "@/types/cart"

export const useCartStore = defineStore("cart", () => {
  const items = ref<CartItem[]>([])

  const count = computed(() => items.value.length)

  function addItem(plugin: Plugin) {
    if (hasItem(plugin.plugin_id)) return
    items.value.push({
      pluginId: plugin.plugin_id,
      name: plugin.name,
      org: plugin.org,
      latestVersion: plugin.latest_version,
      source: "marketplace",
    })
  }

  function hasItem(pluginId: string): boolean {
    return items.value.some((item) => item.pluginId === pluginId)
  }

  function removeItem(pluginId: string) {
    const index = items.value.findIndex((item) => item.pluginId === pluginId)
    if (index !== -1) {
      items.value.splice(index, 1)
    }
  }

  function clearAll() {
    items.value = []
  }

  return {
    items,
    count,
    addItem,
    hasItem,
    removeItem,
    clearAll,
  }
})
