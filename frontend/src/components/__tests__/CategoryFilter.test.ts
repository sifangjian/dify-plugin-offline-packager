import { describe, it, expect } from "vitest"
import { mount } from "@vue/test-utils"
import CategoryFilter from "@/components/CategoryFilter.vue"

describe("CategoryFilter", () => {
  it("should render 6 category buttons", () => {
    const wrapper = mount(CategoryFilter, { props: { category: "" } })
    const buttons = wrapper.findAll("button")
    expect(buttons).toHaveLength(6)
  })

  it("should render correct category labels", () => {
    const wrapper = mount(CategoryFilter, { props: { category: "" } })
    const texts = wrapper.findAll("button").map((b) => b.text())
    expect(texts).toEqual(["全部", "Model", "Tool", "Agent Strategy", "Extension", "Bundle"])
  })

  it("should highlight selected category with blue style", () => {
    const wrapper = mount(CategoryFilter, { props: { category: "tool" } })
    const buttons = wrapper.findAll("button")
    const toolButton = buttons[2]
    expect(toolButton.classes()).toContain("bg-blue-500")
    expect(toolButton.classes()).toContain("text-white")
  })

  it("should show non-selected categories with gray style", () => {
    const wrapper = mount(CategoryFilter, { props: { category: "tool" } })
    const buttons = wrapper.findAll("button")
    const allButton = buttons[0]
    expect(allButton.classes()).toContain("bg-gray-100")
  })

  it("should emit update:category when clicking unselected category", async () => {
    const wrapper = mount(CategoryFilter, { props: { category: "" } })
    const toolButton = wrapper.findAll("button")[2]
    await toolButton.trigger("click")
    expect(wrapper.emitted("update:category")).toBeTruthy()
    expect(wrapper.emitted("update:category")![0]).toEqual(["tool"])
  })

  it("should emit update:category with current value when clicking selected category", async () => {
    const wrapper = mount(CategoryFilter, { props: { category: "tool" } })
    const toolButton = wrapper.findAll("button")[2]
    await toolButton.trigger("click")
    expect(wrapper.emitted("update:category")).toBeTruthy()
    expect(wrapper.emitted("update:category")![0]).toEqual(["tool"])
  })

  it("should use rounded-full pill style", () => {
    const wrapper = mount(CategoryFilter, { props: { category: "" } })
    const buttons = wrapper.findAll("button")
    expect(buttons[0].classes()).toContain("rounded-full")
  })

  it("should have overflow-x-auto on container", () => {
    const wrapper = mount(CategoryFilter, { props: { category: "" } })
    const container = wrapper.find(".overflow-x-auto")
    expect(container.exists()).toBe(true)
  })
})
