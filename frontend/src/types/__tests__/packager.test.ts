import { describe, it, expect } from "vitest"
import type {
  PackStep,
  TaskStatus,
  PackRequest,
  PackResponse,
  SSEEvent,
  PackTaskProgress,
  StepLog,
} from "@/types/packager"
import {
  STEP_LABELS,
  STEP_ORDER,
} from "@/types/packager"

describe("types/packager", () => {
  describe("STEP_ORDER", () => {
    it("should contain 4 steps in correct order", () => {
      expect(STEP_ORDER).toEqual([
        "downloading",
        "resolving_deps",
        "downloading_deps",
        "packaging",
      ])
    })

    it("should have unique values", () => {
      expect(new Set(STEP_ORDER).size).toBe(STEP_ORDER.length)
    })
  })

  describe("STEP_LABELS", () => {
    it("should map each PackStep to a Chinese label", () => {
      expect(STEP_LABELS.downloading).toBe("正在下载插件包...")
      expect(STEP_LABELS.resolving_deps).toBe("正在解析依赖...")
      expect(STEP_LABELS.downloading_deps).toBe("正在下载依赖包...")
      expect(STEP_LABELS.packaging).toBe("正在打包离线插件...")
    })

    it("should have a label for every step in STEP_ORDER", () => {
      for (const step of STEP_ORDER) {
        expect(STEP_LABELS[step]).toBeDefined()
        expect(typeof STEP_LABELS[step]).toBe("string")
      }
    })
  })

  describe("PackStep type", () => {
    it("should accept valid PackStep values", () => {
      const steps: PackStep[] = [
        "downloading",
        "resolving_deps",
        "downloading_deps",
        "packaging",
      ]
      expect(steps).toHaveLength(4)
    })
  })

  describe("TaskStatus type", () => {
    it("should accept valid TaskStatus values", () => {
      const statuses: TaskStatus[] = [
        "pending",
        "running",
        "success",
        "failed",
        "cancelled",
      ]
      expect(statuses).toHaveLength(5)
    })
  })

  describe("SSEEvent discriminated union", () => {
    it("should narrow SessionStartedEvent by event_type", () => {
      const event: SSEEvent = {
        event_type: "session_started",
        session_id: "s-1",
        timestamp: "2024-01-01T00:00:00Z",
        total: 3,
      }
      if (event.event_type === "session_started") {
        expect(event.total).toBe(3)
      }
    })

    it("should narrow TaskStartedEvent by event_type", () => {
      const event: SSEEvent = {
        event_type: "task_started",
        session_id: "s-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "t-1",
        plugin_name: "google",
        plugin_version: "1.0.0",
      }
      if (event.event_type === "task_started") {
        expect(event.task_id).toBe("t-1")
        expect(event.plugin_name).toBe("google")
      }
    })

    it("should narrow StepProgressEvent by event_type", () => {
      const event: SSEEvent = {
        event_type: "step_progress",
        session_id: "s-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "t-1",
        plugin_name: "google",
        step: "resolving_deps",
        message: "正在解析依赖...",
      }
      if (event.event_type === "step_progress") {
        expect(event.step).toBe("resolving_deps")
        expect(event.message).toBe("正在解析依赖...")
      }
    })

    it("should narrow TaskSuccessEvent by event_type", () => {
      const event: SSEEvent = {
        event_type: "task_success",
        session_id: "s-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "t-1",
        plugin_name: "google",
        plugin_version: "1.0.0",
      }
      if (event.event_type === "task_success") {
        expect(event.task_id).toBe("t-1")
      }
    })

    it("should narrow TaskFailedEvent by event_type", () => {
      const event: SSEEvent = {
        event_type: "task_failed",
        session_id: "s-1",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "t-1",
        plugin_name: "google",
        step: "downloading_deps",
        message: "下载依赖包失败",
        raw_error: "ConnectionTimeout",
      }
      if (event.event_type === "task_failed") {
        expect(event.message).toBe("下载依赖包失败")
        expect(event.raw_error).toBe("ConnectionTimeout")
        expect(event.step).toBe("downloading_deps")
      }
    })

    it("should narrow SessionCompletedEvent by event_type", () => {
      const event: SSEEvent = {
        event_type: "session_completed",
        session_id: "s-1",
        timestamp: "2024-01-01T00:00:00Z",
        success_count: 2,
        failed_count: 1,
      }
      if (event.event_type === "session_completed") {
        expect(event.success_count).toBe(2)
        expect(event.failed_count).toBe(1)
      }
    })
  })

  describe("PackTaskProgress interface", () => {
    it("should create a valid PackTaskProgress object", () => {
      const progress: PackTaskProgress = {
        taskId: "t-1",
        sessionId: "s-1",
        author: "langgenius",
        name: "google-search",
        version: "1.0.0",
        status: "pending",
        currentStep: null,
        stepMessage: null,
        errorMessage: null,
        rawError: null,
        logs: [],
        downloaded: false,
      }
      expect(progress.taskId).toBe("t-1")
      expect(progress.status).toBe("pending")
      expect(progress.downloaded).toBe(false)
    })

    it("should support running state with step info", () => {
      const log: StepLog = {
        step: "resolving_deps",
        message: "正在解析依赖...",
        timestamp: "2024-01-01T00:00:00Z",
      }
      const progress: PackTaskProgress = {
        taskId: "t-1",
        sessionId: "s-1",
        author: "langgenius",
        name: "google-search",
        version: "1.0.0",
        status: "running",
        currentStep: "resolving_deps",
        stepMessage: "正在解析依赖...",
        errorMessage: null,
        rawError: null,
        logs: [log],
        downloaded: false,
      }
      expect(progress.currentStep).toBe("resolving_deps")
      expect(progress.logs).toHaveLength(1)
    })

    it("should support failed state with error info", () => {
      const errorLog: StepLog = {
        step: "downloading_deps",
        message: "下载依赖包失败",
        timestamp: "2024-01-01T00:00:00Z",
        isError: true,
      }
      const progress: PackTaskProgress = {
        taskId: "t-1",
        sessionId: "s-1",
        author: "langgenius",
        name: "google-search",
        version: "1.0.0",
        status: "failed",
        currentStep: null,
        stepMessage: null,
        errorMessage: "下载依赖包失败",
        rawError: "ConnectionTimeout",
        logs: [errorLog],
        downloaded: false,
      }
      expect(progress.errorMessage).toBe("下载依赖包失败")
      expect(progress.rawError).toBe("ConnectionTimeout")
      expect(progress.logs[0].isError).toBe(true)
    })
  })

  describe("PackRequest and PackResponse", () => {
    it("should create a valid PackRequest", () => {
      const request: PackRequest = {
        plugins: [
          { author: "langgenius", name: "google", version: "1.0.0", source: "marketplace" },
        ],
      }
      expect(request.plugins).toHaveLength(1)
      expect(request.plugins[0].source).toBe("marketplace")
    })

    it("should create a valid PackResponse", () => {
      const response: PackResponse = {
        session_id: "s-1",
        tasks: [
          {
            task_id: "t-1",
            author: "langgenius",
            name: "google",
            version: "1.0.0",
            status: "pending",
          },
        ],
      }
      expect(response.session_id).toBe("s-1")
      expect(response.tasks).toHaveLength(1)
      expect(response.tasks[0].status).toBe("pending")
    })
  })
})
