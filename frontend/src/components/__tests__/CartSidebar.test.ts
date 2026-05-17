import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { createRouter, createMemoryHistory } from "vue-router"
import CartSidebar from "@/components/CartSidebar.vue"
import { useCartStore } from "@/stores/cart"
import type { Plugin } from "@/types/marketplace"

let mockIsPacking = false
const mockAppendPack = vi.fn()

vi.mock("@/stores/packager", () => ({
  usePackagerStore: () => ({
    isPacking: mockIsPacking,
    appendPack: mockAppendPack,
    startPackFromCart: vi.fn(),
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

describe("CartSidebar", () => {
  let router: ReturnType<typeof createRouter>

  beforeEach(async () => {
    sessionStorage.clear()
    setActivePinia(createPinia())
    mockIsPacking = false
    mockAppendPack.mockReset()

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/", name: "search", component: { template: "<div/>" } },
        { path: "/package", name: "package", component: { template: "<div/>" } },
      ],
    })
    router.push("/")
    await router.isReady()
  })

  it("should hide sidebar with translate-x-full when isOpen is false", () => {
    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    const panel = wrapper.find("[data-testid='sidebar-panel']")
    expect(panel.classes()).toContain("translate-x-full")
  })

  it("should show sidebar with translate-x-0 when isOpen is true", async () => {
    const cartStore = useCartStore()
    cartStore.openSidebar()

    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    const panel = wrapper.find("[data-testid='sidebar-panel']")
    expect(panel.classes()).toContain("translate-x-0")
  })

  it("should show overlay when isOpen is true", async () => {
    const cartStore = useCartStore()
    cartStore.openSidebar()

    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    const overlay = wrapper.find("[data-testid='sidebar-overlay']")
    expect(overlay.exists()).toBe(true)
  })

  it("should not show overlay when isOpen is false", () => {
    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    const overlay = wrapper.find("[data-testid='sidebar-overlay']")
    expect(overlay.exists()).toBe(false)
  })

  it("should close sidebar when overlay is clicked", async () => {
    const cartStore = useCartStore()
    cartStore.openSidebar()

    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    const overlay = wrapper.find("[data-testid='sidebar-overlay']")
    await overlay.trigger("click")

    expect(cartStore.isOpen).toBe(false)
  })

  it("should close sidebar when close button is clicked", async () => {
    const cartStore = useCartStore()
    cartStore.openSidebar()

    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    const closeBtn = wrapper.find("[data-testid='close-sidebar-btn']")
    await closeBtn.trigger("click")

    expect(cartStore.isOpen).toBe(false)
  })

  it("should show empty state when cart is empty", () => {
    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    expect(wrapper.text()).toContain("打包列表为空，去搜索添加插件吧")
  })

  it("should disable start-pack button when cart is empty", () => {
    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    const btn = wrapper.find("[data-testid='start-pack-btn']")
    expect(btn.attributes("disabled")).toBeDefined()
    expect(btn.classes()).toContain("bg-gray-300")
  })

  it("should not show clear button when cart is empty", () => {
    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    const clearBtn = wrapper.find("[data-testid='clear-all-btn']")
    expect(clearBtn.exists()).toBe(false)
  })

  it("should show 2 CartItems and title with count when cart has 2 items", () => {
    const cartStore = useCartStore()
    cartStore.addItem(createMockPlugin({ plugin_id: "p1" }))
    cartStore.addItem(createMockPlugin({ plugin_id: "p2" }))

    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    const items = wrapper.findAllComponents({ name: "CartItem" })
    expect(items).toHaveLength(2)

    const title = wrapper.find("[data-testid='cart-title']")
    expect(title.text()).toContain("打包列表")
    expect(title.text()).toContain("2")
  })

  it("should clear all items when clear button is clicked", async () => {
    const cartStore = useCartStore()
    cartStore.addItem(createMockPlugin({ plugin_id: "p1" }))
    cartStore.addItem(createMockPlugin({ plugin_id: "p2" }))

    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    const clearBtn = wrapper.find("[data-testid='clear-all-btn']")
    await clearBtn.trigger("click")

    expect(cartStore.isEmpty).toBe(true)
  })

  it("should close sidebar and navigate to /package when start-pack is clicked", async () => {
    const cartStore = useCartStore()
    cartStore.addItem(createMockPlugin())

    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    const startBtn = wrapper.find("[data-testid='start-pack-btn']")
    await startBtn.trigger("click")
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(cartStore.isOpen).toBe(false)
    expect(router.currentRoute.value.path).toBe("/package")
  })

  it("should have w-96 width and max-w-full", () => {
    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    const panel = wrapper.find("[data-testid='sidebar-panel']")
    expect(panel.classes()).toContain("w-96")
    expect(panel.classes()).toContain("max-w-full")
  })

  it("should show append-pack button when isPacking is true", () => {
    mockIsPacking = true
    const cartStore = useCartStore()
    cartStore.addItem(createMockPlugin())

    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    expect(wrapper.find("[data-testid='append-pack-btn']").exists()).toBe(true)
    expect(wrapper.find("[data-testid='start-pack-btn']").exists()).toBe(false)
  })

  it("should show start-pack button when isPacking is false", () => {
    mockIsPacking = false
    const cartStore = useCartStore()
    cartStore.addItem(createMockPlugin())

    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    expect(wrapper.find("[data-testid='start-pack-btn']").exists()).toBe(true)
    expect(wrapper.find("[data-testid='append-pack-btn']").exists()).toBe(false)
  })

  it("should call appendPack when append-pack button is clicked", async () => {
    mockIsPacking = true
    const cartStore = useCartStore()
    cartStore.addItem(createMockPlugin())

    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    const appendBtn = wrapper.find("[data-testid='append-pack-btn']")
    await appendBtn.trigger("click")

    expect(mockAppendPack).toHaveBeenCalledWith(cartStore.items)
    expect(cartStore.isOpen).toBe(false)
  })

  it("should disable append-pack button when cart is empty", () => {
    mockIsPacking = true
    const wrapper = mount(CartSidebar, { global: { plugins: [router] } })
    const appendBtn = wrapper.find("[data-testid='append-pack-btn']")
    expect(appendBtn.attributes("disabled")).toBeDefined()
  })
})
