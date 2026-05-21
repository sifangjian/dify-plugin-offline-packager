import { describe, it, expect, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { createRouter, createMemoryHistory } from "vue-router"
import App from "@/App.vue"
import NavBar from "@/components/NavBar.vue"

describe("App.vue layout", () => {
  let router: ReturnType<typeof createRouter>

  beforeEach(async () => {
    sessionStorage.clear()
    localStorage.clear()
    setActivePinia(createPinia())

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: "/",
          name: "workspace",
          component: { template: "<div data-testid='workspace-view'>WorkspaceView</div>" },
        },
        {
          path: "/plugin/:author/:name",
          name: "plugin-detail",
          component: { template: "<div data-testid='detail-view'>DetailView</div>" },
        },
      ],
    })

    router.push("/")
    await router.isReady()
  })

  it("should contain NavBar component", () => {
    const wrapper = mount(App, {
      global: { plugins: [router] },
    })
    expect(wrapper.findComponent(NavBar).exists()).toBe(true)
  })

  it("should have pt-14 padding on main content area", () => {
    const wrapper = mount(App, {
      global: { plugins: [router] },
    })
    const main = wrapper.find("main")
    expect(main.exists()).toBe(true)
    expect(main.classes()).toContain("pt-14")
  })

  it("should display NavBar with application name", () => {
    const wrapper = mount(App, {
      global: { plugins: [router] },
    })
    expect(wrapper.text()).toContain("Dify Plugin Offline Packager")
  })

  it("should not contain CartSidebar", () => {
    const wrapper = mount(App, {
      global: { plugins: [router] },
    })
    const sidebar = wrapper.find("[data-testid='cart-sidebar']")
    expect(sidebar.exists()).toBe(false)
  })
})
