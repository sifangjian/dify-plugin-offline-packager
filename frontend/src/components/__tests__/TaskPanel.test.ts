import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import TaskPanel from "@/components/TaskPanel.vue"

let mockTaskList: Array<Record<string, unknown>> = []
let mockHasTasks = false

vi.mock("@/stores/packager", () => ({
  usePackagerStore: () => ({
    taskList: mockTaskList,
    hasTasks: mockHasTasks,
    isPacking: false,
    cancelPack: vi.fn(),
    clearCompleted: vi.fn(),
    downloadResult: vi.fn(),
    retryFailed: vi.fn(),
  }),
}))

describe("TaskPanel", () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    setActivePinia(createPinia())
    mockTaskList = []
    mockHasTasks = false
  })

  it("should render empty state when no tasks", () => {
    const wrapper = mount(TaskPanel, {
      global: { plugins: [createPinia()] },
    })
    expect(wrapper.find("[data-testid='empty-state']").exists()).toBe(true)
  })

  it("should display task panel header", () => {
    const wrapper = mount(TaskPanel, {
      global: { plugins: [createPinia()] },
    })
    expect(wrapper.text()).toContain("打包任务")
  })

  it("should show clear completed button when there are completed tasks", () => {
    mockTaskList = [
      { taskId: "1", status: "success", name: "test", author: "a", version: "1.0", architecture: "linux-amd64", logs: [], downloaded: false },
    ]
    mockHasTasks = true

    const wrapper = mount(TaskPanel, {
      global: { plugins: [createPinia()] },
    })
    const clearBtn = wrapper.find("[data-testid='clear-completed-btn']")
    expect(clearBtn.exists()).toBe(true)
  })
})
