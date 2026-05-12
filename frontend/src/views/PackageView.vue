<script setup lang="ts">
import { onMounted } from "vue"
import { useRouter } from "vue-router"
import { usePackagerStore } from "@/stores/packager"
import PackageLog from "@/components/PackageLog.vue"

const router = useRouter()
const packagerStore = usePackagerStore()

onMounted(() => {
  packagerStore.restoreSessions()
})

function goSearch(): void {
  router.push({ name: "search" })
}
</script>

<template>
  <div class="p-6 max-w-3xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">
        打包插件
      </h1>
      <button
        v-if="packagerStore.isPacking"
        class="px-4 py-2 text-sm text-red-600 border border-red-300 rounded-lg hover:bg-red-50"
        @click="packagerStore.cancelPack()"
      >
        取消打包
      </button>
    </div>

    <div
      v-if="packagerStore.connectionError"
      class="mb-4 p-3 rounded-lg bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm flex items-center justify-between"
    >
      <span>{{ packagerStore.connectionError }}</span>
      <button
        class="text-yellow-600 hover:text-yellow-800"
        @click="packagerStore.clearConnectionError()"
      >
        ✕
      </button>
    </div>

    <div
      v-if="!packagerStore.hasTasks"
      class="flex flex-col items-center justify-center py-20 text-gray-400"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="w-16 h-16"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="1.5"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
        />
      </svg>
      <p class="mt-4 text-sm">
        打包列表为空，请先添加插件到打包列表
      </p>
      <button
        data-testid="go-search-btn"
        class="mt-4 px-4 py-2 text-sm text-blue-600 border border-blue-300 rounded-lg hover:bg-blue-50"
        @click="goSearch"
      >
        去搜索插件
      </button>
    </div>

    <div
      v-else
      class="flex flex-col gap-4"
    >
      <PackageLog
        v-for="task in packagerStore.taskList"
        :key="task.taskId"
        :task="task"
      />
    </div>
  </div>
</template>
