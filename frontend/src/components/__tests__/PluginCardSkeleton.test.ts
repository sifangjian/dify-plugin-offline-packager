import { describe, it, expect } from "vitest"
import { mount } from "@vue/test-utils"
import PluginCardSkeleton from "@/components/PluginCardSkeleton.vue"

describe("PluginCardSkeleton", () => {
  it("should render with animate-pulse class", () => {
    const wrapper = mount(PluginCardSkeleton)
    expect(wrapper.find(".animate-pulse").exists()).toBe(true)
  })

  it("should render icon placeholder with w-10 h-10 rounded", () => {
    const wrapper = mount(PluginCardSkeleton)
    const icon = wrapper.find(".animate-pulse .w-10.h-10.rounded")
    expect(icon.exists()).toBe(true)
  })

  it("should render title placeholder with h-4 w-3/4", () => {
    const wrapper = mount(PluginCardSkeleton)
    const title = wrapper.find(".animate-pulse .h-4.w-3\\/4")
    expect(title.exists()).toBe(true)
  })

  it("should render subtitle placeholder with h-3 w-1/2", () => {
    const wrapper = mount(PluginCardSkeleton)
    const subtitle = wrapper.find(".animate-pulse .h-3.w-1\\/2")
    expect(subtitle.exists()).toBe(true)
  })

  it("should render description placeholders with 2 lines of h-3", () => {
    const wrapper = mount(PluginCardSkeleton)
    const descriptions = wrapper.findAll(".animate-pulse .h-3.bg-gray-200")
    expect(descriptions.length).toBeGreaterThanOrEqual(2)
  })

  it("should render bottom area with tag and button placeholders", () => {
    const wrapper = mount(PluginCardSkeleton)
    const bottom = wrapper.find(".animate-pulse .mt-3.flex.items-center.justify-between")
    expect(bottom.exists()).toBe(true)
  })

  it("should not accept any props", () => {
    const wrapper = mount(PluginCardSkeleton)
    expect(Object.keys(wrapper.vm.$props)).toHaveLength(0)
  })
})
