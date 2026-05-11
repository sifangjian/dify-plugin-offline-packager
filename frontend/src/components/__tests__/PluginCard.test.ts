import { describe, it, expect, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import PluginCard from "@/components/PluginCard.vue"
import type { Plugin } from "@/types/marketplace"

function createMockPlugin(overrides: Partial<Plugin> = {}): Plugin {
  return {
    type: "tool",
    name: "google-search",
    org: "langgenius",
    plugin_id: "langgenius/google-search",
    icon: "https://example.com/icon.png",
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

  it("should display icon when provided", () => {
    const plugin = createMockPlugin({ icon: "https://example.com/icon.png" })
    const wrapper = mount(PluginCard, { props: { plugin } })
    const img = wrapper.find("img")
    expect(img.exists()).toBe(true)
    expect(img.attributes("src")).toBe("https://example.com/icon.png")
  })

  it("should display default placeholder when icon is empty", () => {
    const plugin = createMockPlugin({ icon: "" })
    const wrapper = mount(PluginCard, { props: { plugin } })
    const img = wrapper.find("img")
    expect(img.exists()).toBe(true)
    expect(img.attributes("src")).toBe("/default-icon.svg")
  })

  it("should show add button when plugin is not in cart", () => {
    const plugin = createMockPlugin()
    const wrapper = mount(PluginCard, { props: { plugin } })
    const btn = wrapper.find("button")
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toBe("添加")
    expect(btn.classes()).toContain("bg-blue-500")
    expect(btn.attributes("disabled")).toBeUndefined()
  })

  it("should show disabled button when plugin is already in cart", async () => {
    const plugin = createMockPlugin()
    const wrapper = mount(PluginCard, { props: { plugin } })
    const btn = wrapper.find("button")
    await btn.trigger("click")

    const wrapper2 = mount(PluginCard, { props: { plugin } })
    const btn2 = wrapper2.find("button")
    expect(btn2.text()).toBe("已添加")
    expect(btn2.classes()).toContain("bg-gray-300")
    expect(btn2.attributes("disabled")).toBeDefined()
  })

  it("should add plugin to cart on button click", async () => {
    const plugin = createMockPlugin()
    const wrapper = mount(PluginCard, { props: { plugin } })
    const btn = wrapper.find("button")
    await btn.trigger("click")

    const { useCartStore } = await import("@/stores/cart")
    const cartStore = useCartStore()
    expect(cartStore.hasItem(plugin.plugin_id)).toBe(true)
  })

  it("should restore add button after removing plugin from cart", async () => {
    const plugin = createMockPlugin()
    const wrapper = mount(PluginCard, { props: { plugin } })
    const btn = wrapper.find("button")
    await btn.trigger("click")

    const { useCartStore } = await import("@/stores/cart")
    const cartStore = useCartStore()
    cartStore.removeItem(plugin.plugin_id)
    await wrapper.vm.$nextTick()

    const wrapper2 = mount(PluginCard, { props: { plugin } })
    const btn2 = wrapper2.find("button")
    expect(btn2.text()).toBe("添加")
    expect(btn2.classes()).toContain("bg-blue-500")
    expect(btn2.attributes("disabled")).toBeUndefined()
  })
})
