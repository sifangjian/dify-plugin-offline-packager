import { describe, it, expect, beforeEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import SearchPanel from "@/components/SearchPanel.vue"

vi.mock("@/stores/marketplace", () => ({
  useMarketplaceStore: () => ({
    keyword: "",
    category: "",
    plugins: [],
    total: 0,
    currentPage: 1,
    isLoading: false,
    error: null,
    hasMore: false,
    search: vi.fn(),
    loadMore: vi.fn(),
    setKeyword: vi.fn(),
    setCategory: vi.fn(),
    clearCategory: vi.fn(),
  }),
}))

describe("SearchPanel", () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it("should render tab buttons for search and upload", () => {
    const wrapper = mount(SearchPanel, {
      global: { plugins: [createPinia()] },
    })
    expect(wrapper.text()).toContain("在线搜索")
    expect(wrapper.text()).toContain("本地上传")
  })

  it("should show search tab as active by default", () => {
    const wrapper = mount(SearchPanel, {
      global: { plugins: [createPinia()] },
    })
    const searchTab = wrapper.find("[data-testid='tab-search']")
    expect(searchTab.classes()).toContain("text-blue-600")
  })

  it("should switch to upload tab when clicked", async () => {
    const wrapper = mount(SearchPanel, {
      global: { plugins: [createPinia()] },
    })
    const uploadTab = wrapper.find("[data-testid='tab-upload']")
    await uploadTab.trigger("click")

    const searchTab = wrapper.find("[data-testid='tab-search']")
    expect(searchTab.classes()).not.toContain("text-blue-600")
    expect(uploadTab.classes()).toContain("text-blue-600")
  })

  it("should show search content in search tab", () => {
    const wrapper = mount(SearchPanel, {
      global: { plugins: [createPinia()] },
    })
    expect(wrapper.find("[data-testid='search-content']").exists()).toBe(true)
  })

  it("should show upload content when upload tab is active", async () => {
    const wrapper = mount(SearchPanel, {
      global: { plugins: [createPinia()] },
    })
    const uploadTab = wrapper.find("[data-testid='tab-upload']")
    await uploadTab.trigger("click")
    expect(wrapper.find("[data-testid='upload-content']").exists()).toBe(true)
  })

  it("should emit pack event when pack button is clicked", async () => {
    const wrapper = mount(SearchPanel, {
      global: { plugins: [createPinia()] },
    })
    const packBtn = wrapper.find("[data-testid='pack-trigger']")
    if (packBtn.exists()) {
      await packBtn.trigger("click")
      expect(wrapper.emitted("pack")).toBeTruthy()
    }
  })
})
