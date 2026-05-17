import { describe, it, expect, vi, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import PackageLog from "@/components/PackageLog.vue"
import type { PackTaskProgress } from "@/types/packager"

const mockDownloadResult = vi.fn()
const mockRetryFailed = vi.fn()

vi.mock("@/stores/packager", () => ({
  usePackagerStore: () => ({
    downloadResult: mockDownloadResult,
    retryFailed: mockRetryFailed,
  }),
}))

function createTask(overrides: Partial<PackTaskProgress> = {}): PackTaskProgress {
  return {
    taskId: "task-1",
    sessionId: "session-1",
    author: "langgenius",
    name: "google-search",
    version: "1.0.0",
    status: "pending",
    currentStep: null,
    stepMessage: null,
    stepDetail: null,
    progress: null,
    errorMessage: null,
    rawError: null,
    logs: [],
    downloaded: false,
    ...overrides,
  }
}

describe("PackageLog", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockDownloadResult.mockReset()
    mockRetryFailed.mockReset()
  })

  describe("pending status", () => {
    it("should display pending badge", () => {
      const wrapper = mount(PackageLog, {
        props: { task: createTask({ status: "pending" }) },
      })

      expect(wrapper.text()).toContain("排队中")
    })
  })

  describe("running status", () => {
    it("should display running badge", () => {
      const wrapper = mount(PackageLog, {
        props: { task: createTask({ status: "running" }) },
      })

      expect(wrapper.text()).toContain("打包中")
    })

    it("should display step indicator when currentStep is set", () => {
      const wrapper = mount(PackageLog, {
        props: {
          task: createTask({
            status: "running",
            currentStep: "resolving_deps",
            stepMessage: "正在解析依赖...",
          }),
        },
      })

      expect(wrapper.text()).toContain("2/4")
      expect(wrapper.text()).toContain("正在解析依赖...")
    })

    it("should show log panel auto-expanded when running", () => {
      const wrapper = mount(PackageLog, {
        props: { task: createTask({ status: "running" }) },
      })

      expect(wrapper.text()).toContain("收起日志")
    })

    it("should show log entries in auto-expanded panel", async () => {
      const task = createTask({
        status: "running",
        currentStep: "resolving_deps",
        stepMessage: "正在解析依赖...",
        logs: [
          { step: "downloading", message: "正在下载插件包...", timestamp: "2024-01-01T00:00:00Z" },
          { step: "resolving_deps", message: "正在解析依赖...", timestamp: "2024-01-01T00:00:05Z" },
        ],
      })
      const wrapper = mount(PackageLog, {
        props: { task },
      })

      expect(wrapper.text()).toContain("正在下载插件包...")
      expect(wrapper.text()).toContain("正在解析依赖...")
    })

    it("should collapse log on click and expand on second click", async () => {
      const task = createTask({
        status: "running",
        logs: [
          { step: "downloading", message: "正在下载插件包...", timestamp: "2024-01-01T00:00:00Z" },
        ],
      })
      const wrapper = mount(PackageLog, {
        props: { task },
      })

      expect(wrapper.text()).toContain("收起日志")

      await wrapper.find("[data-testid='toggle-log-btn']").trigger("click")
      expect(wrapper.text()).toContain("查看详细日志")

      await wrapper.find("[data-testid='toggle-log-btn']").trigger("click")
      expect(wrapper.text()).toContain("收起日志")
    })
  })

  describe("success status", () => {
    it("should display success badge", () => {
      const wrapper = mount(PackageLog, {
        props: { task: createTask({ status: "success" }) },
      })

      expect(wrapper.text()).toContain("打包完成")
    })

    it("should display download button", () => {
      const wrapper = mount(PackageLog, {
        props: { task: createTask({ status: "success" }) },
      })

      expect(wrapper.find("[data-testid='download-btn']").exists()).toBe(true)
      expect(wrapper.find("[data-testid='download-btn']").text()).toBe("下载")
    })

    it("should display re-download button when downloaded", () => {
      const wrapper = mount(PackageLog, {
        props: { task: createTask({ status: "success", downloaded: true }) },
      })

      expect(wrapper.find("[data-testid='download-btn']").text()).toBe("重新下载")
    })

    it("should call downloadResult on download click", async () => {
      const wrapper = mount(PackageLog, {
        props: { task: createTask({ status: "success" }) },
      })

      await wrapper.find("[data-testid='download-btn']").trigger("click")

      expect(mockDownloadResult).toHaveBeenCalledWith("task-1")
    })
  })

  describe("failed status", () => {
    it("should display failed badge", () => {
      const wrapper = mount(PackageLog, {
        props: { task: createTask({ status: "failed" }) },
      })

      expect(wrapper.text()).toContain("失败")
    })

    it("should display error message", () => {
      const wrapper = mount(PackageLog, {
        props: { task: createTask({ status: "failed", errorMessage: "下载依赖包失败" }) },
      })

      expect(wrapper.text()).toContain("下载依赖包失败")
    })

    it("should display retry button", () => {
      const wrapper = mount(PackageLog, {
        props: { task: createTask({ status: "failed" }) },
      })

      expect(wrapper.find("[data-testid='retry-btn']").exists()).toBe(true)
    })

    it("should call retryFailed on retry click", async () => {
      const wrapper = mount(PackageLog, {
        props: { task: createTask({ status: "failed" }) },
      })

      await wrapper.find("[data-testid='retry-btn']").trigger("click")

      expect(mockRetryFailed).toHaveBeenCalledWith("task-1")
    })

    it("should show raw error on expand", async () => {
      const task = createTask({
        status: "failed",
        errorMessage: "下载依赖包失败",
        rawError: "ConnectionTimeout at line 42",
        logs: [
          { step: "downloading_deps", message: "下载依赖包失败", timestamp: "2024-01-01T00:00:00Z", isError: true },
        ],
      })
      const wrapper = mount(PackageLog, {
        props: { task },
      })

      await wrapper.find("[data-testid='toggle-log-btn']").trigger("click")

      expect(wrapper.text()).toContain("ConnectionTimeout at line 42")
    })
  })

  describe("cancelled status", () => {
    it("should display cancelled badge", () => {
      const wrapper = mount(PackageLog, {
        props: { task: createTask({ status: "cancelled" }) },
      })

      expect(wrapper.text()).toContain("已取消")
    })

    it("should display retry button", () => {
      const wrapper = mount(PackageLog, {
        props: { task: createTask({ status: "cancelled" }) },
      })

      expect(wrapper.find("[data-testid='retry-btn']").exists()).toBe(true)
    })
  })
})
