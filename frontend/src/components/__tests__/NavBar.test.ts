import { describe, it, expect, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import NavBar from "@/components/NavBar.vue"
import { useCartStore } from "@/stores/cart"
import type { Plugin } from "@/types/marketplace"

function createMockPlugin(overrides: Partial<Plugin> = {}): Plugin {
  return {
    type: "tool",
    name: "google-search",
    org: "langgenius",
    plugin_id: "langgenius/google-search",
    icon: "",
    label: { en_US: "Google Search", zh_Hans: "谷歌搜索" },
    brief: { en_US: "Search with Google", zh_Hans: "使用谷歌搜索" },
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

describe("NavBar", () => {
  beforeEach(() => {
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  it("should display application name", () => {
    const wrapper = mount(NavBar)
    expect(wrapper.text()).toContain("Dify Plugin Offline Packager")
  })

  it("should contain a cart icon button", () => {
    const wrapper = mount(NavBar)
    const btn = wrapper.find("button")
    expect(btn.exists()).toBe(true)
  })

  it("should not show badge when cart is empty", () => {
    const wrapper = mount(NavBar)
    const badge = wrapper.find("[data-testid='cart-badge']")
    expect(badge.exists()).toBe(false)
  })

  it("should show badge with number 1 after adding one plugin", async () => {
    const cartStore = useCartStore()
    cartStore.addItem(createMockPlugin())

    const wrapper = mount(NavBar)
    const badge = wrapper.find("[data-testid='cart-badge']")
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe("1")
  })

  it("should show badge with number 3 after adding three plugins", async () => {
    const cartStore = useCartStore()
    cartStore.addItem(createMockPlugin({ plugin_id: "p1" }))
    cartStore.addItem(createMockPlugin({ plugin_id: "p2" }))
    cartStore.addItem(createMockPlugin({ plugin_id: "p3" }))

    const wrapper = mount(NavBar)
    const badge = wrapper.find("[data-testid='cart-badge']")
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe("3")
  })

  it("should toggle sidebar when cart icon button is clicked", async () => {
    const cartStore = useCartStore()
    const wrapper = mount(NavBar)
    const btn = wrapper.find("button")

    expect(cartStore.isOpen).toBe(false)
    await btn.trigger("click")
    expect(cartStore.isOpen).toBe(true)
    await btn.trigger("click")
    expect(cartStore.isOpen).toBe(false)
  })

  it("should be fixed at top of page", () => {
    const wrapper = mount(NavBar)
    const header = wrapper.find("header")
    expect(header.classes()).toContain("fixed")
  })
})
