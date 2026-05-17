import { describe, it, expect, vi, beforeEach } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import type { SSEEvent, PackResponse } from "@/types/packager"

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

const STORAGE_KEY = "dify-plugin-packager"

function createMockPlugin(overrides: Partial<Plugin> = {}): Plugin {
  return {
    type: "tool",
    name: "google-search",
    org: "langgenius",
    plugin_id: "langgenius/google-search",
    label: { en_US: "Google Search", zh_Hans: "谷歌搜索" },
    brief: { en_US: "Search", zh_Hans: "搜索" },
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

describe("usePackagerStore", () => {
  beforeEach(() => {
    sessionStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockStartPack.mockReset()
    mockCancelSession.mockReset()
    mockGetDownloadUrl.mockReset()
    mockConnect.mockReset()
    mockDisconnect.mockReset()
  })

  describe("initial state", () => {
    it("should have empty sessions and tasks by default", () => {
      const store = usePackagerStore()
      expect(store.sessions.size).toBe(0)
      expect(store.tasks.size).toBe(0)
    })

    it("should have isPacking as false by default", () => {
      const store = usePackagerStore()
      expect(store.isPacking).toBe(false)
    })

    it("should have hasTasks as false by default", () => {
      const store = usePackagerStore()
      expect(store.hasTasks).toBe(false)
    })

    it("should have empty taskList by default", () => {
      const store = usePackagerStore()
      expect(store.taskList).toEqual([])
    })

    it("should have null connectionError by default", () => {
      const store = usePackagerStore()
      expect(store.connectionError).toBeNull()
    })
  })

  describe("startPackFromCart", () => {
    it("should call startPack API with correct plugin items", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()

      await store.startPackFromCart([createMockPlugin()])

      expect(mockStartPack).toHaveBeenCalledWith({
        plugins: [
          {
            author: "langgenius",
            name: "google-search",
            version: "1.0.0",
            source: "marketplace",
          },
        ],
      })
    })

    it("should create session and tasks from response", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()

      await store.startPackFromCart([createMockPlugin()])

      expect(store.sessions.size).toBe(1)
      expect(store.sessions.has("session-1")).toBe(true)
      expect(store.tasks.size).toBe(1)
      expect(store.tasks.has("task-1")).toBe(true)
    })

    it("should create tasks with pending status", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()

      await store.startPackFromCart([createMockPlugin()])

      const task = store.tasks.get("task-1")!
      expect(task.status).toBe("pending")
      expect(task.currentStep).toBeNull()
      expect(task.downloaded).toBe(false)
    })

    it("should connect SSE after submitting pack", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()

      await store.startPackFromCart([createMockPlugin()])

      expect(mockConnect).toHaveBeenCalledWith("session-1")
    })

    it("should clear connectionError on new pack", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()
      store.connectionError = "some error"

      await store.startPackFromCart([createMockPlugin()])

      expect(store.connectionError).toBeNull()
    })

    it("should persist state to sessionStorage", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()

      await store.startPackFromCart([createMockPlugin()])

      const stored = sessionStorage.getItem(STORAGE_KEY)
      expect(stored).not.toBeNull()
      const parsed = JSON.parse(stored!)
      expect(parsed.sessions).toHaveLength(1)
      expect(parsed.tasks).toHaveLength(1)
    })
  })

  describe("handleSSEEvent", () => {
    async function setupStoreWithTask(): Promise<ReturnType<typeof usePackagerStore>> {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()
      await store.startPackFromCart([createMockPlugin()])
      return store
    }

    it("should update task to running on task_started event", async () => {
      const store = await setupStoreWithTask()
      const event: SSEEvent = {
        event_type: "task_started",
        session_id: "session-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "task-1",
        plugin_name: "google-search",
        plugin_version: "1.0.0",
      }
      store.handleSSEEvent(event)

      expect(store.tasks.get("task-1")!.status).toBe("running")
    })

    it("should update currentStep and stepMessage on step_progress event", async () => {
      const store = await setupStoreWithTask()
      const event: SSEEvent = {
        event_type: "step_progress",
        session_id: "session-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "task-1",
        plugin_name: "google-search",
        step: "resolving_deps",
        message: "正在解析依赖...",
      }
      store.handleSSEEvent(event)

      const task = store.tasks.get("task-1")!
      expect(task.status).toBe("running")
      expect(task.currentStep).toBe("resolving_deps")
      expect(task.stepMessage).toBe("正在解析依赖...")
      expect(task.logs).toHaveLength(1)
      expect(task.logs[0].step).toBe("resolving_deps")
    })

    it("should update task to success on task_success event", async () => {
      const store = await setupStoreWithTask()
      const event: SSEEvent = {
        event_type: "task_success",
        session_id: "session-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "task-1",
        plugin_name: "google-search",
        plugin_version: "1.0.0",
      }
      store.handleSSEEvent(event)

      const task = store.tasks.get("task-1")!
      expect(task.status).toBe("success")
      expect(task.stepMessage).toBe("打包完成")
    })

    it("should update task to failed on task_failed event", async () => {
      const store = await setupStoreWithTask()
      const event: SSEEvent = {
        event_type: "task_failed",
        session_id: "session-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "task-1",
        plugin_name: "google-search",
        step: "downloading_deps",
        message: "下载依赖包失败",
        raw_error: "ConnectionTimeout",
      }
      store.handleSSEEvent(event)

      const task = store.tasks.get("task-1")!
      expect(task.status).toBe("failed")
      expect(task.errorMessage).toBe("下载依赖包失败")
      expect(task.rawError).toBe("ConnectionTimeout")
      expect(task.logs.some((l) => l.isError)).toBe(true)
    })

    it("should mark session as completed on session_completed event", async () => {
      const store = await setupStoreWithTask()
      const event: SSEEvent = {
        event_type: "session_completed",
        session_id: "session-1",
        timestamp: "2024-01-01T00:00:00Z",
        success_count: 1,
        failed_count: 0,
      }
      store.handleSSEEvent(event)

      expect(store.sessions.get("session-1")!.completed).toBe(true)
    })
  })

  describe("computed properties", () => {
    it("isPacking should be true when there are pending tasks", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()

      await store.startPackFromCart([createMockPlugin()])

      expect(store.isPacking).toBe(true)
    })

    it("isPacking should be true when there are running tasks", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()

      await store.startPackFromCart([createMockPlugin()])

      store.handleSSEEvent({
        event_type: "task_started",
        session_id: "session-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "task-1",
        plugin_name: "google-search",
        plugin_version: "1.0.0",
      })

      expect(store.isPacking).toBe(true)
    })

    it("isPacking should be false when all tasks are completed", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()

      await store.startPackFromCart([createMockPlugin()])

      store.handleSSEEvent({
        event_type: "task_success",
        session_id: "session-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "task-1",
        plugin_name: "google-search",
        plugin_version: "1.0.0",
      })

      expect(store.isPacking).toBe(false)
    })

    it("hasTasks should be true when tasks exist", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()

      await store.startPackFromCart([createMockPlugin()])

      expect(store.hasTasks).toBe(true)
    })

    it("taskList should return array of all tasks", async () => {
      mockStartPack.mockResolvedValue(createPackResponse({
        tasks: [
          { task_id: "task-1", author: "a", name: "n1", version: "1.0.0", status: "pending" },
          { task_id: "task-2", author: "b", name: "n2", version: "2.0.0", status: "pending" },
        ],
      }))
      const store = usePackagerStore()

      await store.startPackFromCart([createMockPlugin()])

      expect(store.taskList).toHaveLength(2)
    })
  })

  describe("sessionStorage persistence", () => {
    it("should restore state from sessionStorage on initialization", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store1 = usePackagerStore()
      await store1.startPackFromCart([createMockPlugin()])

      setActivePinia(createPinia())
      const store2 = usePackagerStore()

      expect(store2.sessions.size).toBe(1)
      expect(store2.tasks.size).toBe(1)
    })
  })

  describe("clearConnectionError", () => {
    it("should clear connectionError", () => {
      const store = usePackagerStore()
      store.connectionError = "some error"
      store.clearConnectionError()
      expect(store.connectionError).toBeNull()
    })
  })

  describe("downloadResult", () => {
    it("should trigger browser download for successful task", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()
      await store.startPackFromCart([createMockPlugin()])

      store.handleSSEEvent({
        event_type: "task_success",
        session_id: "session-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "task-1",
        plugin_name: "google-search",
        plugin_version: "1.0.0",
      })

      const clickSpy = vi.fn()
      const appendChildSpy = vi.spyOn(document, "appendChild").mockImplementation((node) => node)
      const removeChildSpy = vi.spyOn(document, "removeChild").mockImplementation((node) => node)
      vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(clickSpy)

      store.downloadResult("task-1")

      expect(clickSpy).toHaveBeenCalled()
      expect(store.tasks.get("task-1")!.downloaded).toBe(true)

      appendChildSpy.mockRestore()
      removeChildSpy.mockRestore()
    })

    it("should not download for non-success task", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()
      await store.startPackFromCart([createMockPlugin()])

      const clickSpy = vi.fn()
      vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(clickSpy)

      store.downloadResult("task-1")

      expect(clickSpy).not.toHaveBeenCalled()
      expect(store.tasks.get("task-1")!.downloaded).toBe(false)
    })
  })

  describe("cancelPack", () => {
    it("should call cancelSession API for active sessions", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      mockCancelSession.mockResolvedValue(undefined)
      const store = usePackagerStore()
      await store.startPackFromCart([createMockPlugin()])

      await store.cancelPack()

      expect(mockCancelSession).toHaveBeenCalledWith("session-1")
    })

    it("should mark pending and running tasks as cancelled", async () => {
      mockStartPack.mockResolvedValue(createPackResponse({
        tasks: [
          { task_id: "task-1", author: "a", name: "n1", version: "1.0.0", status: "pending" },
          { task_id: "task-2", author: "b", name: "n2", version: "2.0.0", status: "pending" },
        ],
      }))
      mockCancelSession.mockResolvedValue(undefined)
      const store = usePackagerStore()
      await store.startPackFromCart([createMockPlugin()])

      store.handleSSEEvent({
        event_type: "task_started",
        session_id: "session-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "task-1",
        plugin_name: "n1",
        plugin_version: "1.0.0",
      })

      await store.cancelPack()

      expect(store.tasks.get("task-1")!.status).toBe("cancelled")
      expect(store.tasks.get("task-2")!.status).toBe("cancelled")
    })

    it("should not affect success tasks", async () => {
      mockStartPack.mockResolvedValue(createPackResponse({
        tasks: [
          { task_id: "task-1", author: "a", name: "n1", version: "1.0.0", status: "pending" },
          { task_id: "task-2", author: "b", name: "n2", version: "2.0.0", status: "pending" },
        ],
      }))
      mockCancelSession.mockResolvedValue(undefined)
      const store = usePackagerStore()
      await store.startPackFromCart([createMockPlugin()])

      store.handleSSEEvent({
        event_type: "task_success",
        session_id: "session-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "task-1",
        plugin_name: "n1",
        plugin_version: "1.0.0",
      })

      await store.cancelPack()

      expect(store.tasks.get("task-1")!.status).toBe("success")
      expect(store.tasks.get("task-2")!.status).toBe("cancelled")
    })

    it("should disconnect SSE and mark sessions as completed", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      mockCancelSession.mockResolvedValue(undefined)
      const store = usePackagerStore()
      await store.startPackFromCart([createMockPlugin()])

      await store.cancelPack()

      expect(mockDisconnect).toHaveBeenCalled()
      expect(store.sessions.get("session-1")!.completed).toBe(true)
    })

    it("should set isPacking to false after cancel", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      mockCancelSession.mockResolvedValue(undefined)
      const store = usePackagerStore()
      await store.startPackFromCart([createMockPlugin()])

      expect(store.isPacking).toBe(true)
      await store.cancelPack()
      expect(store.isPacking).toBe(false)
    })
  })

  describe("retryFailed", () => {
    it("should delete failed task and resubmit", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()
      await store.startPackFromCart([createMockPlugin()])

      store.handleSSEEvent({
        event_type: "task_failed",
        session_id: "session-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "task-1",
        plugin_name: "google-search",
        step: "downloading_deps",
        message: "下载依赖包失败",
        raw_error: "ConnectionTimeout",
      })

      mockStartPack.mockResolvedValue(createPackResponse({
        session_id: "session-2",
        tasks: [{ task_id: "task-2", author: "langgenius", name: "google-search", version: "1.0.0", status: "pending" }],
      }))

      store.retryFailed("task-1")

      expect(store.tasks.has("task-1")).toBe(false)
      expect(mockStartPack).toHaveBeenCalledTimes(2)
    })

    it("should delete cancelled task and resubmit", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      mockCancelSession.mockResolvedValue(undefined)
      const store = usePackagerStore()
      await store.startPackFromCart([createMockPlugin()])

      await store.cancelPack()

      mockStartPack.mockResolvedValue(createPackResponse({
        session_id: "session-2",
        tasks: [{ task_id: "task-2", author: "langgenius", name: "google-search", version: "1.0.0", status: "pending" }],
      }))

      store.retryFailed("task-1")

      expect(store.tasks.has("task-1")).toBe(false)
      expect(mockStartPack).toHaveBeenCalledTimes(2)
    })

    it("should not retry non-failed and non-cancelled task", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()
      await store.startPackFromCart([createMockPlugin()])

      store.retryFailed("task-1")

      expect(mockStartPack).toHaveBeenCalledTimes(1)
    })
  })

  describe("restoreSessions", () => {
    it("should reconnect SSE for incomplete sessions after page refresh", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store1 = usePackagerStore()
      await store1.startPackFromCart([createMockPlugin()])

      setActivePinia(createPinia())
      mockConnect.mockReset()
      const store2 = usePackagerStore()
      store2.restoreSessions()

      expect(mockConnect).toHaveBeenCalledWith("session-1")
    })

    it("should not reconnect SSE for completed sessions", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store1 = usePackagerStore()
      await store1.startPackFromCart([createMockPlugin()])

      store1.handleSSEEvent({
        event_type: "session_completed",
        session_id: "session-1",
        timestamp: "2024-01-01T00:00:00Z",
        success_count: 1,
        failed_count: 0,
      })

      setActivePinia(createPinia())
      mockConnect.mockReset()
      const store2 = usePackagerStore()
      store2.restoreSessions()

      expect(mockConnect).not.toHaveBeenCalled()
    })
  })

  describe("clearCompleted", () => {
    it("should remove completed sessions and their tasks", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()
      await store.startPackFromCart([createMockPlugin()])

      store.handleSSEEvent({
        event_type: "task_success",
        session_id: "session-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "task-1",
        plugin_name: "google-search",
        plugin_version: "1.0.0",
      })
      store.handleSSEEvent({
        event_type: "session_completed",
        session_id: "session-1",
        timestamp: "2024-01-01T00:00:00Z",
        success_count: 1,
        failed_count: 0,
      })

      store.clearCompleted()

      expect(store.sessions.size).toBe(0)
      expect(store.tasks.size).toBe(0)
    })

    it("should not remove incomplete sessions", async () => {
      mockStartPack.mockResolvedValue(createPackResponse())
      const store = usePackagerStore()
      await store.startPackFromCart([createMockPlugin()])

      store.clearCompleted()

      expect(store.sessions.size).toBe(1)
      expect(store.tasks.size).toBe(1)
    })
  })
})
