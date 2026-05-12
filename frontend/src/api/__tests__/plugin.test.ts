import { describe, it, expect, vi, beforeEach } from "vitest"

const mockPost = vi.fn()

vi.mock("@/api/client", () => ({
  default: {
    post: mockPost,
    defaults: {
      baseURL: "/api",
    },
  },
}))

describe("Plugin API", () => {
  beforeEach(() => {
    vi.resetModules()
    mockPost.mockReset()
  })

  describe("startPack", () => {
    it("should send POST request to /v1/plugins/pack", async () => {
      const mockResponse = {
        session_id: "session-123",
        tasks: [
          {
            task_id: "task-1",
            author: "google",
            name: "search",
            version: "1.0.0",
            status: "pending",
          },
        ],
      }
      mockPost.mockResolvedValue({ data: mockResponse })

      const { startPack } = await import("@/api/plugin")

      const result = await startPack({
        plugins: [
          { author: "google", name: "search", version: "1.0.0", source: "marketplace" },
        ],
      })

      expect(mockPost).toHaveBeenCalledWith("/v1/plugins/pack", {
        plugins: [
          { author: "google", name: "search", version: "1.0.0", source: "marketplace" },
        ],
      })
      expect(result).toEqual(mockResponse)
    })

    it("should return PackResponse with session_id and tasks array", async () => {
      const mockResponse = {
        session_id: "session-456",
        tasks: [
          {
            task_id: "task-1",
            author: "langgenius",
            name: "weather",
            version: "2.0.0",
            status: "pending",
          },
          {
            task_id: "task-2",
            author: "langgenius",
            name: "agent",
            version: "1.5.0",
            status: "pending",
          },
        ],
      }
      mockPost.mockResolvedValue({ data: mockResponse })

      const { startPack } = await import("@/api/plugin")

      const result = await startPack({
        plugins: [
          { author: "langgenius", name: "weather", version: "2.0.0", source: "marketplace" },
          { author: "langgenius", name: "agent", version: "1.5.0", source: "marketplace" },
        ],
      })

      expect(result.session_id).toBe("session-456")
      expect(result.tasks).toHaveLength(2)
    })
  })

  describe("cancelSession", () => {
    it("should send POST request to /v1/plugins/cancel/{sessionId}", async () => {
      mockPost.mockResolvedValue({ data: { message: "已取消" } })

      const { cancelSession } = await import("@/api/plugin")

      await cancelSession("session-123")

      expect(mockPost).toHaveBeenCalledWith("/v1/plugins/cancel/session-123")
    })
  })

  describe("getDownloadUrl", () => {
    it("should return correct download URL for a task", async () => {
      const { getDownloadUrl } = await import("@/api/plugin")

      const url = getDownloadUrl("task-456")

      expect(url).toBe("/api/v1/plugins/download/task-456")
    })

    it("should include different task IDs in the URL", async () => {
      const { getDownloadUrl } = await import("@/api/plugin")

      const url = getDownloadUrl("another-task-id")

      expect(url).toBe("/api/v1/plugins/download/another-task-id")
    })
  })
})
