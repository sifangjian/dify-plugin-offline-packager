import { describe, it, expect, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import CartItem from "@/components/CartItem.vue"
import { useCartStore } from "@/stores/cart"
import type { Plugin } from "@/types/marketplace"

function createMockPlugin(overrides: Partial<Plugin> = {}): Plugin {
  return {
    type: "tool",
    name: "test-plugin",
    org: "test",
    plugin_id: "test/test-plugin",
    icon: "https://example.com/icon.png",
    label: { en_US: "Test Plugin", zh_Hans: "测试插件" },
    brief: { en_US: "A test plugin", zh_Hans: "一个测试插件" },
    introduction: "",
    category: "Tool",
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

describe("CartItem", () => {
  beforeEach(() => {
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  it("should display icon, name, author, version, category, and remove button", () => {
    const plugin = createMockPlugin()
    const wrapper = mount(CartItem, { props: { plugin } })

    const img = wrapper.find("img")
    expect(img.exists()).toBe(true)
    expect(img.attributes("src")).toBe("https://example.com/icon.png")

    expect(wrapper.text()).toContain("测试插件")
    expect(wrapper.text()).toContain("test")
    expect(wrapper.text()).toContain("1.0.0")
    expect(wrapper.text()).toContain("Tool")

    const removeBtn = wrapper.find("[data-testid='remove-item-btn']")
    expect(removeBtn.exists()).toBe(true)
  })

  it("should display en_US name when zh_Hans is empty", () => {
    const plugin = createMockPlugin({
      label: { en_US: "Test Plugin", zh_Hans: "" },
    })
    const wrapper = mount(CartItem, { props: { plugin } })
    expect(wrapper.text()).toContain("Test Plugin")
  })

  it("should display default placeholder when icon is empty", () => {
    const plugin = createMockPlugin({ icon: "" })
    const wrapper = mount(CartItem, { props: { plugin } })
    const img = wrapper.find("img")
    expect(img.exists()).toBe(false)
    const placeholder = wrapper.find("[data-testid='default-icon']")
    expect(placeholder.exists()).toBe(true)
  })

  it("should not display category tag when category is empty", () => {
    const plugin = createMockPlugin({ category: "" })
    const wrapper = mount(CartItem, { props: { plugin } })
    const tag = wrapper.find("[data-testid='category-tag']")
    expect(tag.exists()).toBe(false)
  })

  it("should call cartStore.removeItem when remove button is clicked", async () => {
    const plugin = createMockPlugin()
    const cartStore = useCartStore()
    cartStore.addItem(plugin)

    const wrapper = mount(CartItem, { props: { plugin } })
    const removeBtn = wrapper.find("[data-testid='remove-item-btn']")
    await removeBtn.trigger("click")

    expect(cartStore.hasItem(plugin.plugin_id)).toBe(false)
  })

  it("should truncate long name with truncate class", () => {
    const plugin = createMockPlugin({
      label: { en_US: "", zh_Hans: "这是一个非常非常非常非常非常非常长的插件名称用来测试截断效果" },
    })
    const wrapper = mount(CartItem, { props: { plugin } })
    const nameEl = wrapper.find("[data-testid='plugin-name']")
    expect(nameEl.classes()).toContain("truncate")
  })
})
