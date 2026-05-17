import { describe, it, expect, beforeEach } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import { useCartStore } from "@/stores/cart"
import type { Plugin } from "@/types/marketplace"

const STORAGE_KEY = "dify-plugin-cart"

function createMockPlugin(overrides: Partial<Plugin> = {}): Plugin {
  return {
    type: "tool",
    name: "google-search",
    org: "langgenius",
    plugin_id: "langgenius/google-search",
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
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  describe("initial state", () => {
    it("should have empty items by default", () => {
      const store = useCartStore()
      expect(store.items).toEqual([])
    })

    it("should have itemCount of 0 by default", () => {
      const store = useCartStore()
      expect(store.itemCount).toBe(0)
    })

    it("should have isEmpty as true by default", () => {
      const store = useCartStore()
      expect(store.isEmpty).toBe(true)
    })

    it("should have isOpen as false by default", () => {
      const store = useCartStore()
      expect(store.isOpen).toBe(false)
    })
  })

  describe("addItem", () => {
    it("should add a plugin to items", () => {
      const store = useCartStore()
      const plugin = createMockPlugin()
      store.addItem(plugin)

      expect(store.items).toHaveLength(1)
      expect(store.itemCount).toBe(1)
      expect(store.hasItem(plugin.plugin_id)).toBe(true)
    })

    it("should not add duplicate plugin (same plugin_id)", () => {
      const store = useCartStore()
      const plugin = createMockPlugin()
      store.addItem(plugin)
      store.addItem(plugin)

      expect(store.items).toHaveLength(1)
    })

    it("should add multiple different plugins", () => {
      const store = useCartStore()
      const plugin1 = createMockPlugin({ plugin_id: "langgenius/google-search" })
      const plugin2 = createMockPlugin({ plugin_id: "langgenius/weather", name: "weather" })
      store.addItem(plugin1)
      store.addItem(plugin2)

      expect(store.items).toHaveLength(2)
      expect(store.itemCount).toBe(2)
    })

    it("should set isEmpty to false after adding", () => {
      const store = useCartStore()
      store.addItem(createMockPlugin())
      expect(store.isEmpty).toBe(false)
    })

    it("should store full Plugin object", () => {
      const store = useCartStore()
      const plugin = createMockPlugin()
      store.addItem(plugin)

      expect(store.items[0]).toEqual(plugin)
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
    it("should remove item by plugin_id", () => {
      const store = useCartStore()
      store.addItem(createMockPlugin())
      store.removeItem("langgenius/google-search")

      expect(store.items).toHaveLength(0)
      expect(store.hasItem("langgenius/google-search")).toBe(false)
    })

    it("should do nothing when removing non-existent id", () => {
      const store = useCartStore()
      store.addItem(createMockPlugin())
      store.removeItem("non-existent-id")

      expect(store.items).toHaveLength(1)
    })

    it("should update itemCount after removal", () => {
      const store = useCartStore()
      store.addItem(createMockPlugin({ plugin_id: "p1" }))
      store.addItem(createMockPlugin({ plugin_id: "p2" }))
      store.removeItem("p1")

      expect(store.itemCount).toBe(1)
    })

    it("should set isEmpty to true after removing all items", () => {
      const store = useCartStore()
      store.addItem(createMockPlugin())
      store.removeItem("langgenius/google-search")

      expect(store.isEmpty).toBe(true)
    })
  })

  describe("clearAll", () => {
    it("should clear all items", () => {
      const store = useCartStore()
      store.addItem(createMockPlugin({ plugin_id: "p1" }))
      store.addItem(createMockPlugin({ plugin_id: "p2" }))
      store.clearAll()

      expect(store.items).toEqual([])
      expect(store.isEmpty).toBe(true)
      expect(store.itemCount).toBe(0)
    })
  })

  describe("sessionStorage persistence", () => {
    it("should save items to sessionStorage after addItem", () => {
      const store = useCartStore()
      const plugin = createMockPlugin()
      store.addItem(plugin)

      const stored = sessionStorage.getItem(STORAGE_KEY)
      expect(stored).not.toBeNull()
      const parsed = JSON.parse(stored!)
      expect(parsed).toHaveLength(1)
      expect(parsed[0].plugin_id).toBe("langgenius/google-search")
    })

    it("should save items to sessionStorage after removeItem", () => {
      const store = useCartStore()
      store.addItem(createMockPlugin({ plugin_id: "p1" }))
      store.addItem(createMockPlugin({ plugin_id: "p2" }))
      store.removeItem("p1")

      const stored = sessionStorage.getItem(STORAGE_KEY)
      const parsed = JSON.parse(stored!)
      expect(parsed).toHaveLength(1)
      expect(parsed[0].plugin_id).toBe("p2")
    })

    it("should save empty array to sessionStorage after clearAll", () => {
      const store = useCartStore()
      store.addItem(createMockPlugin())
      store.clearAll()

      const stored = sessionStorage.getItem(STORAGE_KEY)
      expect(stored).toBe("[]")
    })

    it("should restore items from sessionStorage on initialization", () => {
      const plugin = createMockPlugin()
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify([plugin]))

      setActivePinia(createPinia())
      const store = useCartStore()

      expect(store.items).toHaveLength(1)
      expect(store.items[0].plugin_id).toBe("langgenius/google-search")
      expect(store.itemCount).toBe(1)
    })

    it("should handle invalid JSON in sessionStorage gracefully", () => {
      sessionStorage.setItem(STORAGE_KEY, "not-valid-json{{{")

      setActivePinia(createPinia())
      const store = useCartStore()

      expect(store.items).toEqual([])
      expect(store.itemCount).toBe(0)
    })

    it("should handle empty sessionStorage", () => {
      sessionStorage.removeItem(STORAGE_KEY)

      setActivePinia(createPinia())
      const store = useCartStore()

      expect(store.items).toEqual([])
    })
  })

  describe("sidebar state", () => {
    it("should open sidebar with openSidebar", () => {
      const store = useCartStore()
      store.openSidebar()
      expect(store.isOpen).toBe(true)
    })

    it("should close sidebar with closeSidebar", () => {
      const store = useCartStore()
      store.openSidebar()
      store.closeSidebar()
      expect(store.isOpen).toBe(false)
    })

    it("should toggle sidebar state with toggleSidebar", () => {
      const store = useCartStore()
      expect(store.isOpen).toBe(false)

      store.toggleSidebar()
      expect(store.isOpen).toBe(true)

      store.toggleSidebar()
      expect(store.isOpen).toBe(false)
    })
  })
})
