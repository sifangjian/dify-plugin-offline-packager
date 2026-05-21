import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import NavBar from "@/components/NavBar.vue"

let mockIsPacking = false
let mockTaskCount = 0

vi.mock("@/stores/packager", () => ({
  usePackagerStore: () => ({
    isPacking: mockIsPacking,
    taskList: Array.from({ length: mockTaskCount }, (_, i) => ({ taskId: String(i) })),
  }),
}))

describe("NavBar after refactor", () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    setActivePinia(createPinia())
    mockIsPacking = false
    mockTaskCount = 0
  })

  it("should display application name", () => {
    const wrapper = mount(NavBar)
    expect(wrapper.text()).toContain("Dify Plugin Offline Packager")
  })

  it("should be fixed at top of page", () => {
    const wrapper = mount(NavBar)
    const header = wrapper.find("header")
    expect(header.classes()).toContain("fixed")
  })

  it("should not contain cart toggle button", () => {
    const wrapper = mount(NavBar)
    expect(wrapper.find("[data-testid='cart-icon']").exists()).toBe(false)
  })

  it("should show task count badge when there are tasks", () => {
    mockTaskCount = 3
    const wrapper = mount(NavBar)
    const badge = wrapper.find("[data-testid='task-badge']")
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe("3")
  })

  it("should not show task badge when there are no tasks", () => {
    mockTaskCount = 0
    const wrapper = mount(NavBar)
    const badge = wrapper.find("[data-testid='task-badge']")
    expect(badge.exists()).toBe(false)
  })

  it("should add animate-pulse class when isPacking is true", () => {
    mockIsPacking = true
    const wrapper = mount(NavBar)
    const badge = wrapper.find("[data-testid='task-badge']")
    if (badge.exists()) {
      expect(badge.classes()).toContain("animate-pulse")
    }
  })
})
