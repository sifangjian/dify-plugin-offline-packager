import { describe, it, expect, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import ArchitectureSelector from "@/components/ArchitectureSelector.vue"
import { ARCHITECTURE_OPTIONS } from "@/types/packager"

describe("ArchitectureSelector", () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  it("should display title '选择目标架构'", () => {
    const wrapper = mount(ArchitectureSelector, {
      props: { modelValue: true, selectedArchitecture: "linux-amd64" },
    })
    expect(wrapper.text()).toContain("选择目标架构")
  })

  it("should render 4 radio options for architectures", () => {
    const wrapper = mount(ArchitectureSelector, {
      props: { modelValue: true, selectedArchitecture: "linux-amd64" },
    })
    for (const option of ARCHITECTURE_OPTIONS) {
      expect(wrapper.find(`[data-testid='arch-option-${option.value}']`).exists()).toBe(true)
    }
  })

  it("should display label and description for each option", () => {
    const wrapper = mount(ArchitectureSelector, {
      props: { modelValue: true, selectedArchitecture: "linux-amd64" },
    })
    for (const option of ARCHITECTURE_OPTIONS) {
      expect(wrapper.text()).toContain(option.label)
      expect(wrapper.text()).toContain(option.description)
    }
  })

  it("should have the selected architecture highlighted", () => {
    const wrapper = mount(ArchitectureSelector, {
      props: { modelValue: true, selectedArchitecture: "linux-arm64" },
    })
    const selectedOption = wrapper.find("[data-testid='arch-option-linux-arm64']")
    expect(selectedOption.classes()).toContain("border-blue-500")
  })

  it("should emit confirm event with selected architecture when confirm button is clicked", async () => {
    const wrapper = mount(ArchitectureSelector, {
      props: { modelValue: true, selectedArchitecture: "linux-amd64" },
    })
    const confirmBtn = wrapper.find("[data-testid='arch-confirm-btn']")
    await confirmBtn.trigger("click")

    expect(wrapper.emitted("confirm")).toBeTruthy()
    expect(wrapper.emitted("confirm")![0]).toEqual(["linux-amd64"])
    expect(wrapper.emitted("update:modelValue")).toBeTruthy()
    expect(wrapper.emitted("update:modelValue")![0]).toEqual([false])
  })

  it("should emit update:modelValue with false when cancel button is clicked", async () => {
    const wrapper = mount(ArchitectureSelector, {
      props: { modelValue: true, selectedArchitecture: "linux-amd64" },
    })
    const cancelBtn = wrapper.find("[data-testid='arch-cancel-btn']")
    await cancelBtn.trigger("click")

    expect(wrapper.emitted("update:modelValue")).toBeTruthy()
    expect(wrapper.emitted("update:modelValue")![0]).toEqual([false])
    expect(wrapper.emitted("confirm")).toBeFalsy()
  })

  it("should not close dialog when overlay is clicked", async () => {
    const wrapper = mount(ArchitectureSelector, {
      props: { modelValue: true, selectedArchitecture: "linux-amd64" },
    })
    const overlay = wrapper.find("[data-testid='arch-overlay']")
    await overlay.trigger("click")

    expect(wrapper.emitted("update:modelValue")).toBeFalsy()
  })

  it("should update selected arch when clicking an option", async () => {
    const wrapper = mount(ArchitectureSelector, {
      props: { modelValue: true, selectedArchitecture: "linux-amd64" },
    })
    const armOption = wrapper.find("[data-testid='arch-option-linux-arm64']")
    await armOption.trigger("click")

    const confirmBtn = wrapper.find("[data-testid='arch-confirm-btn']")
    await confirmBtn.trigger("click")

    expect(wrapper.emitted("confirm")![0]).toEqual(["linux-arm64"])
  })
})
