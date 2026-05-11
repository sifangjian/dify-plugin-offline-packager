import { defineStore } from "pinia"
import { ref, computed } from "vue"
import type { Plugin } from "@/types/marketplace"

const CART_STORAGE_KEY = "dify-plugin-cart"

function saveToStorage(items: Plugin[]): void {
  sessionStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items))
}

function loadFromStorage(): Plugin[] {
  const data = sessionStorage.getItem(CART_STORAGE_KEY)
  if (!data) return []
  try {
    return JSON.parse(data) as Plugin[]
  } catch {
    return []
  }
}

export const useCartStore = defineStore("cart", () => {
  const items = ref<Plugin[]>(loadFromStorage())
  const isOpen = ref(false)

  const itemCount = computed(() => items.value.length)
  const isEmpty = computed(() => items.value.length === 0)

  function hasItem(pluginId: string): boolean {
    return items.value.some((item) => item.plugin_id === pluginId)
  }

  function addItem(plugin: Plugin): void {
    if (hasItem(plugin.plugin_id)) return
    items.value.push(plugin)
    saveToStorage(items.value)
  }

  function removeItem(pluginId: string): void {
    const index = items.value.findIndex((item) => item.plugin_id === pluginId)
    if (index === -1) return
    items.value.splice(index, 1)
    saveToStorage(items.value)
  }

  function clearAll(): void {
    items.value = []
    saveToStorage(items.value)
  }

  function openSidebar(): void {
    isOpen.value = true
  }

  function closeSidebar(): void {
    isOpen.value = false
  }

  function toggleSidebar(): void {
    isOpen.value = !isOpen.value
  }

  return {
    items,
    isOpen,
    itemCount,
    isEmpty,
    hasItem,
    addItem,
    removeItem,
    clearAll,
    openSidebar,
    closeSidebar,
    toggleSidebar,
  }
})
