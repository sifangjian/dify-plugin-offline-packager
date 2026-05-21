<script setup lang="ts">
import { computed } from "vue"
import { usePackagerStore } from "@/stores/packager"
import PackageLog from "@/components/PackageLog.vue"

const packagerStore = usePackagerStore()

const pendingTasks = computed(() =>
  packagerStore.taskList.filter((t) => t.status === "pending"),
)

const runningTasks = computed(() =>
  packagerStore.taskList.filter((t) => t.status === "running"),
)

const completedTasks = computed(() =>
  packagerStore.taskList.filter((t) => t.status === "success"),
)

const failedTasks = computed(() =>
  packagerStore.taskList.filter((t) => t.status === "failed" || t.status === "cancelled"),
)

const hasCompletedOrFailed = computed(() =>
  completedTasks.value.length > 0 || failedTasks.value.length > 0,
)
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200">
      <h2 class="text-sm font-semibold text-gray-900">
        打包任务
        <span
          v-if="packagerStore.hasTasks"
          class="text-gray-500 font-normal"
        >
          ({{ packagerStore.taskList.length }})
        </span>
      </h2>
      <button
        v-if="hasCompletedOrFailed"
        data-testid="clear-completed-btn"
        class="text-xs text-gray-500 hover:text-red-600"
        @click="packagerStore.clearCompleted()"
      >
        清除已完成
      </button>
    </div>

    <div
      v-if="!packagerStore.hasTasks"
      data-testid="empty-state"
      class="flex-1 flex flex-col items-center justify-center text-gray-400"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="w-12 h-12"
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
        暂无打包任务
      </p>
      <p class="text-xs mt-1">
        在左侧搜索并打包插件
      </p>
    </div>

    <div
      v-else
      class="flex-1 overflow-y-auto p-4 flex flex-col gap-4"
    >
      <div v-if="runningTasks.length > 0">
        <h3 class="text-xs font-medium text-blue-600 mb-2">
          进行中 ({{ runningTasks.length }})
        </h3>
        <div class="flex flex-col gap-3">
          <PackageLog
            v-for="task in runningTasks"
            :key="task.taskId"
            :task="task"
          />
        </div>
      </div>

      <div v-if="pendingTasks.length > 0">
        <h3 class="text-xs font-medium text-gray-500 mb-2">
          排队中 ({{ pendingTasks.length }})
        </h3>
        <div class="flex flex-col gap-3">
          <PackageLog
            v-for="task in pendingTasks"
            :key="task.taskId"
            :task="task"
          />
        </div>
      </div>

      <div v-if="completedTasks.length > 0">
        <h3 class="text-xs font-medium text-green-600 mb-2">
          已完成 ({{ completedTasks.length }})
        </h3>
        <div class="flex flex-col gap-3">
          <PackageLog
            v-for="task in completedTasks"
            :key="task.taskId"
            :task="task"
          />
        </div>
      </div>

      <div v-if="failedTasks.length > 0">
        <h3 class="text-xs font-medium text-red-600 mb-2">
          失败 ({{ failedTasks.length }})
        </h3>
        <div class="flex flex-col gap-3">
          <PackageLog
            v-for="task in failedTasks"
            :key="task.taskId"
            :task="task"
          />
        </div>
      </div>
    </div>
  </div>
</template>
