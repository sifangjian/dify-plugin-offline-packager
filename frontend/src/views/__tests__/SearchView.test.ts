import { describe, it, expect, vi, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import SearchView from "@/views/SearchView.vue"
import type { Plugin, SearchResult } from "@/types/marketplace"

const mockSearchPlugins = vi.fn()

vi.mock("@/api/marketplace", () => ({
  searchPlugins: vi.fn(),
}))

import { searchPlugins } from "@/api/marketplace"
vi.mocked(searchPlugins).mockImplementation(mockSearchPlugins)

function createMockPlugin(overrides: Partial<Plugin> = {}): Plugin {
  return {
    type: "tool",
    name: "test-plugin",
    org: "langgenius",
    plugin_id: "langgenius/test-plugin",
    icon: "",
    label: { en_US: "Test Plugin", zh_Hans: "测试插件" },
    brief: { en_US: "A test plugin", zh_Hans: "一个测试插件" },
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

describe("SearchView", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockSearchPlugins.mockReset()
  })

  it("should render sticky search bar with input and button", () => {
    mockSearchPlugins.mockResolvedValue({ plugins: [], total: 0 })
    const wrapper = mount(SearchView, { global: { plugins: [createPinia()] } })
    const header = wrapper.find("header.sticky.top-0")
    expect(header.exists()).toBe(true)
    expect(header.find("input").exists()).toBe(true)
    expect(header.find("button").exists()).toBe(true)
  })

  it("should call store.search() on mount", async () => {
    mockSearchPlugins.mockResolvedValue({ plugins: [], total: 0 })
    mount(SearchView, { global: { plugins: [createPinia()] } })
    await vi.dynamicImportSettled()
    expect(mockSearchPlugins).toHaveBeenCalled()
  })

  it("should render plugin grid with grid-cols-4", async () => {
    const plugins = [createMockPlugin({ plugin_id: "p1" }), createMockPlugin({ plugin_id: "p2" })]
    mockSearchPlugins.mockResolvedValue({ plugins, total: 2 })
    const wrapper = mount(SearchView, { global: { plugins: [createPinia()] } })
    await vi.dynamicImportSettled()
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    const grid = wrapper.find(".grid.grid-cols-4")
    expect(grid.exists()).toBe(true)
  })

  it("should show 8 skeleton cards when loading with no results", async () => {
    let resolveSearch: (value: SearchResult) => void
    mockSearchPlugins.mockReturnValue(new Promise<SearchResult>((resolve) => { resolveSearch = resolve }))
    const wrapper = mount(SearchView, { global: { plugins: [createPinia()] } })
    await vi.dynamicImportSettled()
    await wrapper.vm.$nextTick()
    const skeletons = wrapper.findAllComponents({ name: "PluginCardSkeleton" })
    expect(skeletons.length).toBe(8)
    resolveSearch!({ plugins: [], total: 0 })
  })

  it("should show empty placeholder when no results and not loading", async () => {
    mockSearchPlugins.mockResolvedValue({ plugins: [], total: 0 })
    const wrapper = mount(SearchView, { global: { plugins: [createPinia()] } })
    await vi.dynamicImportSettled()
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    const grid = wrapper.find(".grid.grid-cols-4")
    expect(grid.exists()).toBe(false)
  })

  it("should render PluginCard for each plugin", async () => {
    const plugins = [createMockPlugin({ plugin_id: "p1" }), createMockPlugin({ plugin_id: "p2" })]
    mockSearchPlugins.mockResolvedValue({ plugins, total: 2 })
    const wrapper = mount(SearchView, { global: { plugins: [createPinia()] } })
    await vi.dynamicImportSettled()
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    const cards = wrapper.findAllComponents({ name: "PluginCard" })
    expect(cards.length).toBe(2)
  })
})
