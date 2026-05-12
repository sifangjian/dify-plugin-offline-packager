import { describe, it, expect, vi, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import PackageView from "@/views/PackageView.vue"

const mockRestoreSessions = vi.fn()
const mockCancelPack = vi.fn()
const mockClearConnectionError = vi.fn()

let mockStoreState = {
  isPacking: false,
  hasTasks: false,
  taskList: [] as never[],
  connectionError: null as string | null,
}

vi.mock("@/stores/packager", () => ({
  usePackagerStore: () => ({
    ...mockStoreState,
    restoreSessions: mockRestoreSessions,
    cancelPack: mockCancelPack,
    clearConnectionError: mockClearConnectionError,
  }),
}))

const mockPush = vi.fn()
vi.mock("vue-router", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}))

describe("PackageView", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockRestoreSessions.mockReset()
    mockCancelPack.mockReset()
    mockClearConnectionError.mockReset()
    mockPush.mockReset()
    mockStoreState = {
      isPacking: false,
      hasTasks: false,
      taskList: [],
      connectionError: null,
    }
  })

  it("should call restoreSessions on mount", () => {
    mount(PackageView)
    expect(mockRestoreSessions).toHaveBeenCalled()
  })

  it("should display empty state when no tasks", () => {
    const wrapper = mount(PackageView)
    expect(wrapper.text()).toContain("打包列表为空")
    expect(wrapper.text()).toContain("请先添加插件到打包列表")
  })

  it("should display go search button in empty state", () => {
    const wrapper = mount(PackageView)
    expect(wrapper.find("[data-testid='go-search-btn']").exists()).toBe(true)
  })

  it("should navigate to search page on go search click", async () => {
    const wrapper = mount(PackageView)
    await wrapper.find("[data-testid='go-search-btn']").trigger("click")
    expect(mockPush).toHaveBeenCalledWith({ name: "search" })
  })

  it("should display page title", () => {
    const wrapper = mount(PackageView)
    expect(wrapper.text()).toContain("打包插件")
  })

  it("should show cancel button when isPacking is true", () => {
    mockStoreState.isPacking = true
    mockStoreState.hasTasks = true
    const wrapper = mount(PackageView)
    expect(wrapper.text()).toContain("取消打包")
  })

  it("should not show cancel button when isPacking is false", () => {
    mockStoreState.isPacking = false
    mockStoreState.hasTasks = true
    const wrapper = mount(PackageView)
    expect(wrapper.text()).not.toContain("取消打包")
  })

  it("should show connection error banner when connectionError is set", () => {
    mockStoreState.connectionError = "连接已断开"
    const wrapper = mount(PackageView)
    expect(wrapper.text()).toContain("连接已断开")
  })

  it("should call cancelPack when cancel button is clicked", async () => {
    mockStoreState.isPacking = true
    mockStoreState.hasTasks = true
    const wrapper = mount(PackageView)
    const cancelBtn = wrapper.find("button")
    await cancelBtn.trigger("click")
    expect(mockCancelPack).toHaveBeenCalled()
  })

  it("should call clearConnectionError when error close button is clicked", async () => {
    mockStoreState.connectionError = "连接已断开"
    const wrapper = mount(PackageView)
    const closeBtn = wrapper.findAll("button").find((b) => b.text() === "✕")
    await closeBtn!.trigger("click")
    expect(mockClearConnectionError).toHaveBeenCalled()
  })
})
