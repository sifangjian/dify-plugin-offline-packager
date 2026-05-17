import { describe, it, expect, vi, beforeEach } from "vitest"
import { createPinia, setActivePinia } from "pinia"

vi.mock("@/api/marketplace", () => ({
  searchPlugins: vi.fn(),
}))

import { useMarketplaceStore } from "@/stores/marketplace"
import type { Plugin, SearchResult } from "@/types/marketplace"

import { searchPlugins } from "@/api/marketplace"

const mockSearchPlugins = vi.mocked(searchPlugins)

function createMockPlugin(overrides: Partial<Plugin> = {}): Plugin {
  return {
    type: "tool",
    name: "test-plugin",
    org: "langgenius",
    plugin_id: "langgenius/test-plugin",
    label: { en_US: "Test Plugin", zh_Hans: "测试插件" },
    brief: { en_US: "A test plugin", zh_Hans: "一个测试插件" },
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

describe("useMarketplaceStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockSearchPlugins.mockReset()
  })

  describe("initial state", () => {
    it("should have correct default values", () => {
      const store = useMarketplaceStore()
      expect(store.keyword).toBe("")
      expect(store.plugins).toEqual([])
      expect(store.total).toBe(0)
      expect(store.isLoading).toBe(false)
      expect(store.error).toBeNull()
    })

    it("should have hasMore as false when no results", () => {
      const store = useMarketplaceStore()
      expect(store.hasMore).toBe(false)
    })
  })

  describe("setKeyword", () => {
    it("should update keyword", () => {
      const store = useMarketplaceStore()
      store.setKeyword("google")
      expect(store.keyword).toBe("google")
    })
  })

  describe("search", () => {
    it("should reset state and call searchPlugins with empty params", async () => {
      const mockResult: SearchResult = {
        plugins: [createMockPlugin()],
        total: 1,
      }
      mockSearchPlugins.mockResolvedValue(mockResult)

      const store = useMarketplaceStore()
      await store.search()

      expect(mockSearchPlugins).toHaveBeenCalledWith({
        keyword: "",
        category: "",
        page: 1,
        page_size: 20,
      }, expect.any(AbortSignal))
      expect(store.plugins).toEqual(mockResult.plugins)
      expect(store.total).toBe(1)
      expect(store.isLoading).toBe(false)
      expect(store.error).toBeNull()
    })

    it("should search with keyword", async () => {
      const mockResult: SearchResult = {
        plugins: [createMockPlugin({ name: "google-search" })],
        total: 1,
      }
      mockSearchPlugins.mockResolvedValue(mockResult)

      const store = useMarketplaceStore()
      store.setKeyword("google")
      await store.search()

      expect(mockSearchPlugins).toHaveBeenCalledWith({
        keyword: "google",
        category: "",
        page: 1,
        page_size: 20,
      }, expect.any(AbortSignal))
    })

    it("should clear plugins and set isLoading before search", async () => {
      let resolveSearch: (value: SearchResult) => void
      const searchPromise = new Promise<SearchResult>((resolve) => {
        resolveSearch = resolve
      })
      mockSearchPlugins.mockReturnValue(searchPromise)

      const store = useMarketplaceStore()
      store.setKeyword("test")

      const searchTask = store.search()
      expect(store.isLoading).toBe(true)
      expect(store.plugins).toEqual([])

      resolveSearch!({ plugins: [createMockPlugin()], total: 1 })
      await searchTask

      expect(store.isLoading).toBe(false)
    })

    it("should set error when search fails", async () => {
      mockSearchPlugins.mockRejectedValue({ status: 500, message: "服务异常" })

      const store = useMarketplaceStore()
      await store.search()

      expect(store.error).toBe("服务异常")
      expect(store.isLoading).toBe(false)
      expect(store.plugins).toEqual([])
    })

    it("should compute hasMore correctly", async () => {
      const mockResult: SearchResult = {
        plugins: Array.from({ length: 20 }, (_, i) =>
          createMockPlugin({ plugin_id: `plugin-${i}` })
        ),
        total: 50,
      }
      mockSearchPlugins.mockResolvedValue(mockResult)

      const store = useMarketplaceStore()
      await store.search()

      expect(store.hasMore).toBe(true)
    })

    it("should compute hasMore as false when all loaded", async () => {
      const mockResult: SearchResult = {
        plugins: [createMockPlugin()],
        total: 1,
      }
      mockSearchPlugins.mockResolvedValue(mockResult)

      const store = useMarketplaceStore()
      await store.search()

      expect(store.hasMore).toBe(false)
    })

    it("should clear error on new search", async () => {
      mockSearchPlugins.mockRejectedValue({ status: 500, message: "服务异常" })

      const store = useMarketplaceStore()
      await store.search()
      expect(store.error).toBe("服务异常")

      mockSearchPlugins.mockResolvedValue({ plugins: [], total: 0 })
      await store.search()
      expect(store.error).toBeNull()
    })
  })

  describe("category filtering", () => {
    it("should have empty category by default", () => {
      const store = useMarketplaceStore()
      expect(store.category).toBe("")
    })

    it("should setCategory and auto-trigger search", async () => {
      mockSearchPlugins.mockResolvedValue({ plugins: [], total: 0 })

      const store = useMarketplaceStore()
      store.setCategory("tool")

      expect(store.category).toBe("tool")
      await vi.dynamicImportSettled()
      expect(mockSearchPlugins).toHaveBeenCalledWith({
        keyword: "",
        category: "tool",
        page: 1,
        page_size: 20,
      }, expect.any(AbortSignal))
    })

    it("should clearCategory and auto-trigger search", async () => {
      mockSearchPlugins.mockResolvedValue({ plugins: [], total: 0 })

      const store = useMarketplaceStore()
      store.setCategory("tool")
      store.clearCategory()

      expect(store.category).toBe("")
      await vi.dynamicImportSettled()
      expect(mockSearchPlugins).toHaveBeenCalledWith({
        keyword: "",
        category: "",
        page: 1,
        page_size: 20,
      }, expect.any(AbortSignal))
    })

    it("should search with keyword + category combination", async () => {
      mockSearchPlugins.mockResolvedValue({ plugins: [], total: 0 })

      const store = useMarketplaceStore()
      store.setKeyword("google")
      store.setCategory("tool")

      await vi.dynamicImportSettled()
      expect(mockSearchPlugins).toHaveBeenCalledWith({
        keyword: "google",
        category: "tool",
        page: 1,
        page_size: 20,
      }, expect.any(AbortSignal))
    })

    it("should search all plugins with empty keyword and category", async () => {
      mockSearchPlugins.mockResolvedValue({ plugins: [], total: 0 })

      const store = useMarketplaceStore()
      await store.search()

      expect(mockSearchPlugins).toHaveBeenCalledWith({
        keyword: "",
        category: "",
        page: 1,
        page_size: 20,
      }, expect.any(AbortSignal))
    })

    it("should browse category plugins with empty keyword", async () => {
      mockSearchPlugins.mockResolvedValue({ plugins: [], total: 0 })

      const store = useMarketplaceStore()
      store.setCategory("model")

      await vi.dynamicImportSettled()
      expect(mockSearchPlugins).toHaveBeenCalledWith({
        keyword: "",
        category: "model",
        page: 1,
        page_size: 20,
      }, expect.any(AbortSignal))
    })
  })

  describe("loadMore", () => {
    it("should not load more when isLoading is true", async () => {
      let resolveSearch: (value: SearchResult) => void
      mockSearchPlugins.mockReturnValue(new Promise<SearchResult>((resolve) => { resolveSearch = resolve }))

      const store = useMarketplaceStore()
      store.search()

      await store.loadMore()

      expect(mockSearchPlugins).toHaveBeenCalledTimes(1)
      resolveSearch!({ plugins: [], total: 0 })
    })

    it("should not load more when hasMore is false", async () => {
      mockSearchPlugins.mockResolvedValue({ plugins: [createMockPlugin()], total: 1 })

      const store = useMarketplaceStore()
      await store.search()

      mockSearchPlugins.mockClear()
      await store.loadMore()

      expect(mockSearchPlugins).not.toHaveBeenCalled()
    })

    it("should load next page and append results", async () => {
      const page1Plugins = Array.from({ length: 20 }, (_, i) =>
        createMockPlugin({ plugin_id: `p1-${i}` })
      )
      mockSearchPlugins.mockResolvedValue({ plugins: page1Plugins, total: 40 })

      const store = useMarketplaceStore()
      await store.search()

      expect(store.plugins.length).toBe(20)
      expect(store.currentPage).toBe(1)

      const page2Plugins = Array.from({ length: 20 }, (_, i) =>
        createMockPlugin({ plugin_id: `p2-${i}` })
      )
      mockSearchPlugins.mockResolvedValue({ plugins: page2Plugins, total: 40 })

      await store.loadMore()

      expect(store.plugins.length).toBe(40)
      expect(store.currentPage).toBe(2)
      expect(mockSearchPlugins).toHaveBeenLastCalledWith({
        keyword: "",
        category: "",
        page: 2,
        page_size: 20,
      }, expect.any(AbortSignal))
    })

    it("should set error when loadMore fails", async () => {
      const page1Plugins = Array.from({ length: 20 }, (_, i) =>
        createMockPlugin({ plugin_id: `p1-${i}` })
      )
      mockSearchPlugins.mockResolvedValue({ plugins: page1Plugins, total: 40 })

      const store = useMarketplaceStore()
      await store.search()

      mockSearchPlugins.mockRejectedValue({ status: 500, message: "加载失败" })
      await store.loadMore()

      expect(store.error).toBe("加载失败")
    })
  })

  describe("AbortController", () => {
    it("should reset plugins on new search even if old request resolves later", async () => {
      const page1Plugins = Array.from({ length: 20 }, (_, i) =>
        createMockPlugin({ plugin_id: `p1-${i}` })
      )
      mockSearchPlugins.mockResolvedValue({ plugins: page1Plugins, total: 20 })

      const store = useMarketplaceStore()
      await store.search()

      expect(store.plugins.length).toBe(20)

      mockSearchPlugins.mockResolvedValue({ plugins: [], total: 0 })
      await store.search()

      expect(store.plugins).toEqual([])
      expect(store.total).toBe(0)
    })
  })
})
