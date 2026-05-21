import { describe, it, expect, beforeEach } from "vitest"
import { mount } from "@vue/test-utils"
import { createRouter, createWebHashHistory, type Router } from "vue-router"
import { createPinia, setActivePinia } from "pinia"
import App from "@/App.vue"

describe("App.vue after refactor", () => {
  let router: Router

  beforeEach(async () => {
    sessionStorage.clear()
    localStorage.clear()
    setActivePinia(createPinia())

    router = createRouter({
      history: createWebHashHistory(),
      routes: [
        { path: "/", name: "workspace", component: { template: "<div>Workspace</div>" } },
        { path: "/plugin/:author/:name", name: "plugin-detail", component: { template: "<div>Detail</div>" } },
      ],
    })
    router.push("/")
    await router.isReady()
  })

  it("should not render CartSidebar", () => {
    const wrapper = mount(App, { global: { plugins: [router] } })
    expect(wrapper.find("[data-testid='cart-sidebar']").exists()).toBe(false)
  })

  it("should render NavBar", () => {
    const wrapper = mount(App, { global: { plugins: [router] } })
    expect(wrapper.find("header").exists()).toBe(true)
  })

  it("should render RouterView", () => {
    const wrapper = mount(App, { global: { plugins: [router] } })
    expect(wrapper.text()).toContain("Workspace")
  })
})
