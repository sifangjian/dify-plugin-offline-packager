import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import PluginCard from "@/components/PluginCard.vue"
import type { Plugin } from "@/types/marketplace"

vi.mock("@/stores/packager", () => ({
  usePackagerStore: () => ({
    isInQueue: () => false,
    taskList: [],
  }),
}))

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
    install_count: 15000,
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

describe("PluginCard", () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it("should display plugin name using zh_Hans when available", () => {
    const plugin = createMockPlugin()
    const wrapper = mount(PluginCard, { props: { plugin } })
    expect(wrapper.text()).toContain("谷歌搜索")
  })

  it("should fallback to en_US when zh_Hans is empty", () => {
    const plugin = createMockPlugin({
      label: { en_US: "Google Search", zh_Hans: "" },
    })
    const wrapper = mount(PluginCard, { props: { plugin } })
    expect(wrapper.text()).toContain("Google Search")
  })

  it("should display author (org)", () => {
    const plugin = createMockPlugin()
    const wrapper = mount(PluginCard, { props: { plugin } })
    expect(wrapper.text()).toContain("langgenius")
  })

  it("should display description with line-clamp-2", () => {
    const plugin = createMockPlugin()
    const wrapper = mount(PluginCard, { props: { plugin } })
    const desc = wrapper.find(".line-clamp-2")
    expect(desc.exists()).toBe(true)
    expect(desc.text()).toContain("使用谷歌搜索")
  })

  it("should display category as blue tag", () => {
    const plugin = createMockPlugin()
    const wrapper = mount(PluginCard, { props: { plugin } })
    const tag = wrapper.find(".bg-blue-50.text-blue-600")
    expect(tag.exists()).toBe(true)
    expect(tag.text()).toContain("tool")
  })

  it("should format install count >= 10000 as X.X万", () => {
    const plugin = createMockPlugin({ install_count: 15000 })
    const wrapper = mount(PluginCard, { props: { plugin } })
    expect(wrapper.text()).toContain("1.5万")
  })

  it("should format install count >= 1000 as X.Xk", () => {
    const plugin = createMockPlugin({ install_count: 3500 })
    const wrapper = mount(PluginCard, { props: { plugin } })
    expect(wrapper.text()).toContain("3.5k")
  })

  it("should display install count as-is when < 1000", () => {
    const plugin = createMockPlugin({ install_count: 500 })
    const wrapper = mount(PluginCard, { props: { plugin } })
    expect(wrapper.text()).toContain("500")
  })

  it("should show pack button by default", () => {
    const plugin = createMockPlugin()
    const wrapper = mount(PluginCard, { props: { plugin } })
    const btn = wrapper.find("[data-testid='pack-trigger']")
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toBe("打包")
    expect(btn.classes()).toContain("bg-blue-500")
    expect(btn.attributes("disabled")).toBeUndefined()
  })

  it("should emit pack event when pack button is clicked", async () => {
    const plugin = createMockPlugin()
    const wrapper = mount(PluginCard, { props: { plugin } })
    const btn = wrapper.find("[data-testid='pack-trigger']")
    await btn.trigger("click")
    expect(wrapper.emitted("pack")).toBeTruthy()
    expect(wrapper.emitted("pack")![0]).toEqual([plugin])
  })
})
