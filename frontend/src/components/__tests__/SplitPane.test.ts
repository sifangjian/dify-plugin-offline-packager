import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { mount } from "@vue/test-utils"
import SplitPane from "@/components/SplitPane.vue"

const STORAGE_KEY = "splitpane-left-width"

describe("SplitPane", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("should render left and right slots", () => {
    const wrapper = mount(SplitPane, {
      slots: {
        left: "<div data-testid='left-content'>Left Panel</div>",
        right: "<div data-testid='right-content'>Right Panel</div>",
      },
    })
    expect(wrapper.find("[data-testid='left-content']").exists()).toBe(true)
    expect(wrapper.find("[data-testid='right-content']").exists()).toBe(true)
  })

  it("should apply default 60:40 split ratio", () => {
    const wrapper = mount(SplitPane, {
      slots: {
        left: "<div>Left</div>",
        right: "<div>Right</div>",
      },
    })
    const leftPane = wrapper.find("[data-testid='left-pane']")
    const rightPane = wrapper.find("[data-testid='right-pane']")
    expect(leftPane.attributes("style")).toContain("60%")
    expect(rightPane.attributes("style")).toContain("40%")
  })

  it("should respect custom defaultLeftWidth prop", () => {
    const wrapper = mount(SplitPane, {
      props: { defaultLeftWidth: 50 },
      slots: {
        left: "<div>Left</div>",
        right: "<div>Right</div>",
      },
    })
    const leftPane = wrapper.find("[data-testid='left-pane']")
    expect(leftPane.attributes("style")).toContain("50%")
  })

  it("should render a divider element", () => {
    const wrapper = mount(SplitPane, {
      slots: {
        left: "<div>Left</div>",
        right: "<div>Right</div>",
      },
    })
    const divider = wrapper.find("[data-testid='divider']")
    expect(divider.exists()).toBe(true)
  })

  it("should apply hover style on divider", () => {
    const wrapper = mount(SplitPane, {
      slots: {
        left: "<div>Left</div>",
        right: "<div>Right</div>",
      },
    })
    const divider = wrapper.find("[data-testid='divider']")
    expect(divider.classes().some((c) => c.includes("hover"))).toBe(true)
  })

  it("should clamp left width to minLeftWidth when dragging below minimum", async () => {
    const wrapper = mount(SplitPane, {
      props: { minLeftWidth: 30, minRightWidth: 25 },
      slots: {
        left: "<div>Left</div>",
        right: "<div>Right</div>",
      },
    })

    const vm = wrapper.vm as unknown as { leftWidth: number }
    const divider = wrapper.find("[data-testid='divider']")

    const containerEl = wrapper.element as HTMLElement
    vi.spyOn(containerEl, "getBoundingClientRect").mockReturnValue({
      width: 1000,
      height: 600,
      top: 0,
      left: 0,
      right: 1000,
      bottom: 600,
      x: 0,
      y: 0,
      toJSON: () => {},
    })

    await divider.trigger("mousedown", { clientX: 600 })
    document.dispatchEvent(new MouseEvent("mousemove", { clientX: 50 }))
    document.dispatchEvent(new MouseEvent("mouseup"))

    expect(vm.leftWidth).toBeGreaterThanOrEqual(30)
  })

  it("should clamp right width to minRightWidth when dragging beyond maximum", async () => {
    const wrapper = mount(SplitPane, {
      props: { minLeftWidth: 30, minRightWidth: 25 },
      slots: {
        left: "<div>Left</div>",
        right: "<div>Right</div>",
      },
    })

    const vm = wrapper.vm as unknown as { leftWidth: number }
    const divider = wrapper.find("[data-testid='divider']")

    const containerEl = wrapper.element as HTMLElement
    vi.spyOn(containerEl, "getBoundingClientRect").mockReturnValue({
      width: 1000,
      height: 600,
      top: 0,
      left: 0,
      right: 1000,
      bottom: 600,
      x: 0,
      y: 0,
      toJSON: () => {},
    })

    await divider.trigger("mousedown", { clientX: 600 })
    document.dispatchEvent(new MouseEvent("mousemove", { clientX: 990 }))
    document.dispatchEvent(new MouseEvent("mouseup"))

    expect(vm.leftWidth).toBeLessThanOrEqual(75)
  })

  it("should persist leftWidth to localStorage on drag end", async () => {
    const wrapper = mount(SplitPane, {
      props: { minLeftWidth: 30, minRightWidth: 25 },
      slots: {
        left: "<div>Left</div>",
        right: "<div>Right</div>",
      },
    })

    const divider = wrapper.find("[data-testid='divider']")

    const containerEl = wrapper.element as HTMLElement
    vi.spyOn(containerEl, "getBoundingClientRect").mockReturnValue({
      width: 1000,
      height: 600,
      top: 0,
      left: 0,
      right: 1000,
      bottom: 600,
      x: 0,
      y: 0,
      toJSON: () => {},
    })

    await divider.trigger("mousedown", { clientX: 600 })
    document.dispatchEvent(new MouseEvent("mousemove", { clientX: 700 }))
    document.dispatchEvent(new MouseEvent("mouseup"))

    const stored = localStorage.getItem(STORAGE_KEY)
    expect(stored).not.toBeNull()
  })

  it("should restore leftWidth from localStorage on mount", () => {
    localStorage.setItem(STORAGE_KEY, "45")

    const wrapper = mount(SplitPane, {
      slots: {
        left: "<div>Left</div>",
        right: "<div>Right</div>",
      },
    })

    const leftPane = wrapper.find("[data-testid='left-pane']")
    expect(leftPane.attributes("style")).toContain("45%")
  })

  it("should emit resize event when leftWidth changes", async () => {
    const wrapper = mount(SplitPane, {
      props: { minLeftWidth: 30, minRightWidth: 25 },
      slots: {
        left: "<div>Left</div>",
        right: "<div>Right</div>",
      },
    })

    const divider = wrapper.find("[data-testid='divider']")

    const containerEl = wrapper.element as HTMLElement
    vi.spyOn(containerEl, "getBoundingClientRect").mockReturnValue({
      width: 1000,
      height: 600,
      top: 0,
      left: 0,
      right: 1000,
      bottom: 600,
      x: 0,
      y: 0,
      toJSON: () => {},
    })

    await divider.trigger("mousedown", { clientX: 600 })
    document.dispatchEvent(new MouseEvent("mousemove", { clientX: 700 }))
    document.dispatchEvent(new MouseEvent("mouseup"))

    expect(wrapper.emitted("resize")).toBeTruthy()
    expect(wrapper.emitted("resize")!.length).toBeGreaterThan(0)
  })
})
