import { createRouter, createWebHashHistory } from "vue-router"

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: "/",
      name: "workspace",
      component: () => import("@/views/WorkspaceView.vue"),
    },
    {
      path: "/plugin/:author/:name",
      name: "plugin-detail",
      component: () => import("@/views/PluginDetailView.vue"),
    },
  ],
})

export default router
