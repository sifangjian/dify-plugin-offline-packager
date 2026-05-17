import { createRouter, createWebHashHistory } from "vue-router"

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: "/",
      name: "search",
      component: () => import("@/views/SearchView.vue"),
    },
    {
      path: "/upload",
      name: "upload",
      component: () => import("@/views/UploadView.vue"),
    },
    {
      path: "/plugin/:author/:name",
      name: "plugin-detail",
      component: () => import("@/views/PluginDetailView.vue"),
    },
    {
      path: "/package",
      name: "package",
      component: () => import("@/views/PackageView.vue"),
    },
  ],
})

export default router
