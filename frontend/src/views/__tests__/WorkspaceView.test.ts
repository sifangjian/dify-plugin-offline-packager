import { describe, it, expect, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { createRouter, createWebHashHistory, type Router } from "vue-router"
import { createPinia, setActivePinia } from "pinia"
import WorkspaceView from "@/views/WorkspaceView.vue"

describe("WorkspaceView", () => {
  let router: Router

  beforeEach(async () => {
    sessionStorage.clear()
    localStorage.clear()
    setActivePinia(createPinia())

    router = createRouter({
      history: createWebHashHistory(),
      routes: [
        { path: "/", name: "workspace", component: WorkspaceView },
        { path: "/plugin/:author/:name", name: "plugin-detail", component: { template: "<div>Detail</div>" } },
      ],
    })
    router.push("/")
    await router.isReady()
  })

  it("should render SplitPane component", () => {
    const wrapper = mount(WorkspaceView, {
      global: { plugins: [router, createPinia()] },
    })
    expect(wrapper.find("[data-testid='split-pane']").exists()).toBe(true)
  })

  it("should render left and right panels inside SplitPane", () => {
    const wrapper = mount(WorkspaceView, {
      global: { plugins: [router, createPinia()] },
    })
    expect(wrapper.find("[data-testid='left-pane']").exists()).toBe(true)
    expect(wrapper.find("[data-testid='right-pane']").exists()).toBe(true)
  })
})
