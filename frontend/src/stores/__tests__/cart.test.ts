import { describe, it, expect, beforeEach } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import { useCartStore } from "@/stores/cart"
import type { Plugin } from "@/types/marketplace"

function createMockPlugin(overrides: Partial<Plugin> = {}): Plugin {
  return {
    type: "tool",
    name: "google-search",
    org: "langgenius",
    plugin_id: "langgenius/google-search",
    icon: "",
    label: { en_US: "Google Search", zh_Hans: "谷歌搜索" },
    brief: { en_US: "Search with Google", zh_Hans: "使用谷歌搜索" },
    introduction: "",
    category: "tool",
    created_at: "2024-01-01",
    updated_at: "2024-01-01",
    install_count: 100,
    latest_version: "1.0.0",
    latest_package_identifier: "",
    status: "active",
    tags: [],
    verification: null,
    badges: [],
    repository: null,
    resource: null,
    privacy_policy: "",
    ...overrides,
  }
}

describe("useCartStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe("initial state", () => {
    it("should have empty items by default", () => {
      const store = useCartStore()
      expect(store.items).toEqual([])
    })

    it("should have count of 0 by default", () => {
      const store = useCartStore()
      expect(store.count).toBe(0)
    })
  })

  describe("addItem", () => {
    it("should add a plugin to items", () => {
      const store = useCartStore()
      const plugin = createMockPlugin()
      store.addItem(plugin)

      expect(store.items).toHaveLength(1)
      expect(store.items[0]).toEqual({
        pluginId: "langgenius/google-search",
        name: "google-search",
        org: "langgenius",
        latestVersion: "1.0.0",
        source: "marketplace",
      })
    })

    it("should not add duplicate plugin", () => {
      const store = useCartStore()
      const plugin = createMockPlugin()
      store.addItem(plugin)
      store.addItem(plugin)

      expect(store.items).toHaveLength(1)
    })

    it("should update count after adding", () => {
      const store = useCartStore()
      store.addItem(createMockPlugin())
      expect(store.count).toBe(1)
    })
  })

  describe("hasItem", () => {
    it("should return true when item exists", () => {
      const store = useCartStore()
      store.addItem(createMockPlugin())
      expect(store.hasItem("langgenius/google-search")).toBe(true)
    })

    it("should return false when item does not exist", () => {
      const store = useCartStore()
      expect(store.hasItem("langgenius/google-search")).toBe(false)
    })
  })

  describe("removeItem", () => {
    it("should remove item by pluginId", () => {
      const store = useCartStore()
      store.addItem(createMockPlugin())
      store.removeItem("langgenius/google-search")
      expect(store.items).toHaveLength(0)
    })

    it("should do nothing when removing non-existent item", () => {
      const store = useCartStore()
      store.removeItem("non-existent")
      expect(store.items).toHaveLength(0)
    })
  })

  describe("clearAll", () => {
    it("should clear all items", () => {
      const store = useCartStore()
      store.addItem(createMockPlugin({ plugin_id: "p1" }))
      store.addItem(createMockPlugin({ plugin_id: "p2" }))
      store.clearAll()
      expect(store.items).toHaveLength(0)
      expect(store.count).toBe(0)
    })
  })
})
