import { describe, it, expect, vi, beforeEach } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import type { PackResponse } from "@/types/packager"

const { mockStartPack, mockCancelSession, mockGetDownloadUrl, mockConnect, mockDisconnect } = vi.hoisted(() => ({
  mockStartPack: vi.fn(),
  mockCancelSession: vi.fn(),
  mockGetDownloadUrl: vi.fn(),
  mockConnect: vi.fn(),
  mockDisconnect: vi.fn(),
}))

vi.mock("@/api/plugin", () => ({
  startPack: mockStartPack,
  cancelSession: mockCancelSession,
  getDownloadUrl: mockGetDownloadUrl,
}))

vi.mock("@/composables/useSSE", () => ({
  useSSE: () => ({
    connect: mockConnect,
    disconnect: mockDisconnect,
    isConnected: { value: false },
  }),
}))

import { usePackagerStore } from "@/stores/packager"
import type { Plugin } from "@/types/marketplace"

function createMockPlugin(overrides: Partial<Plugin> = {}): Plugin {
  return {
    type: "tool",
    name: "google-search",
    org: "langgenius",
    plugin_id: "langgenius/google-search",
    label: { en_US: "Google Search", zh_Hans: "谷歌搜索" },
    brief: { en_US: "Search", zh_Hans: "搜索" },
    introduction: "",
    readme_meta: { available_languages: [] },
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

function createPackResponse(overrides: Partial<PackResponse> = {}): PackResponse {
  return {
    session_id: "session-1",
    tasks: [
      {
        task_id: "task-1",
        author: "langgenius",
        name: "google-search",
        version: "1.0.0",
        status: "pending",
      },
    ],
    ...overrides,
  }
}

describe("usePackagerStore queue functionality", () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockStartPack.mockReset()
    mockCancelSession.mockReset()
    mockGetDownloadUrl.mockReset()
    mockConnect.mockReset()
    mockDisconnect.mockReset()
  })

  describe("queuedItems", () => {
    it("should have empty queuedItems by default", () => {
      const store = usePackagerStore()
      expect(store.queuedItems).toEqual([])
    })

    it("should add plugin to queue via enqueuePlugin", () => {
      const store = usePackagerStore()
      const plugin = createMockPlugin()
      store.enqueuePlugin(plugin)
      expect(store.queuedItems).toHaveLength(1)
      expect(store.queuedItems[0].plugin_id).toBe("langgenius/google-search")
    })

    it("should not add duplicate plugin to queue", () => {
      const store = usePackagerStore()
      const plugin = createMockPlugin()
      store.enqueuePlugin(plugin)
      store.enqueuePlugin(plugin)
      expect(store.queuedItems).toHaveLength(1)
    })

    it("should persist queuedItems to sessionStorage", () => {
      const store = usePackagerStore()
      store.enqueuePlugin(createMockPlugin())

      const stored = sessionStorage.getItem("dify-plugin-packager-queue")
      expect(stored).not.toBeNull()
    })

    it("should restore queuedItems from sessionStorage on init", () => {
      const store1 = usePackagerStore()
      store1.enqueuePlugin(createMockPlugin())

      setActivePinia(createPinia())
      const store2 = usePackagerStore()
      expect(store2.queuedItems).toHaveLength(1)
    })
  })

  describe("dequeueAndPack", () => {
    it("should remove plugin from queue and start pack", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()
      const plugin = createMockPlugin()
      store.enqueuePlugin(plugin)

      await store.dequeueAndPack("linux-amd64")

      expect(store.queuedItems).toHaveLength(0)
      expect(mockStartPack).toHaveBeenCalledWith({
        plugins: [
          {
            author: "langgenius",
            name: "google-search",
            version: "1.0.0",
            source: "marketplace",
            architecture: "linux-amd64",
          },
        ],
      })
    })

    it("should create session and tasks from response", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()
      store.enqueuePlugin(createMockPlugin())

      await store.dequeueAndPack("linux-amd64")

      expect(store.sessions.size).toBe(1)
      expect(store.tasks.size).toBe(1)
    })

    it("should connect SSE after dequeue and pack", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()
      store.enqueuePlugin(createMockPlugin())

      await store.dequeueAndPack("linux-amd64")

      expect(mockConnect).toHaveBeenCalledWith("session-1")
    })
  })

  describe("startPackFromQueue", () => {
    it("should pack all queued items and clear queue", async () => {
      mockStartPack.mockResolvedValue(createPackResponse({
        tasks: [
          { task_id: "task-1", author: "langgenius", name: "google-search", version: "1.0.0", status: "pending" },
          { task_id: "task-2", author: "other", name: "other-plugin", version: "2.0.0", status: "pending" },
        ],
      }))
      const store = usePackagerStore()
      store.enqueuePlugin(createMockPlugin())
      store.enqueuePlugin(createMockPlugin({ plugin_id: "other/other-plugin", name: "other-plugin", org: "other", latest_version: "2.0.0" }))

      await store.startPackFromQueue("linux-arm64")

      expect(store.queuedItems).toHaveLength(0)
      expect(mockStartPack).toHaveBeenCalledWith({
        plugins: [
          {
            author: "langgenius",
            name: "google-search",
            version: "1.0.0",
            source: "marketplace",
            architecture: "linux-arm64",
          },
          {
            author: "other",
            name: "other-plugin",
            version: "2.0.0",
            source: "marketplace",
            architecture: "linux-arm64",
          },
        ],
      })
    })
  })

  describe("removeFromQueue", () => {
    it("should remove specific plugin from queue", () => {
      const store = usePackagerStore()
      store.enqueuePlugin(createMockPlugin({ plugin_id: "p1" }))
      store.enqueuePlugin(createMockPlugin({ plugin_id: "p2" }))

      store.removeFromQueue("p1")

      expect(store.queuedItems).toHaveLength(1)
      expect(store.queuedItems[0].plugin_id).toBe("p2")
    })
  })

  describe("clearQueue", () => {
    it("should clear all items from queue", () => {
      const store = usePackagerStore()
      store.enqueuePlugin(createMockPlugin({ plugin_id: "p1" }))
      store.enqueuePlugin(createMockPlugin({ plugin_id: "p2" }))

      store.clearQueue()

      expect(store.queuedItems).toHaveLength(0)
    })
  })

  describe("isInQueue", () => {
    it("should return true if plugin is in queue", () => {
      const store = usePackagerStore()
      store.enqueuePlugin(createMockPlugin())
      expect(store.isInQueue("langgenius/google-search")).toBe(true)
    })

    it("should return false if plugin is not in queue", () => {
      const store = usePackagerStore()
      expect(store.isInQueue("nonexistent")).toBe(false)
    })
  })
})
