<script setup lang="ts">
import { ref, computed } from "vue"
import { usePackagerStore } from "@/stores/packager"
import type { PackTaskProgress } from "@/types/packager"
import { STEP_ORDER } from "@/types/packager"

interface Props {
  task: PackTaskProgress
}
const props = defineProps<Props>()

const packagerStore = usePackagerStore()
const isLogExpanded = ref(false)

const statusConfig = computed(() => {
  const configs: Record<string, { bg: string; border: string; badge: string; label: string }> = {
    pending: { bg: "bg-gray-50", border: "border-gray-200", badge: "bg-gray-100 text-gray-600", label: "排队中" },
    running: { bg: "bg-blue-50", border: "border-blue-200", badge: "bg-blue-100 text-blue-700", label: "打包中" },
    success: { bg: "bg-green-50", border: "border-green-200", badge: "bg-green-100 text-green-700", label: "打包完成" },
    failed: { bg: "bg-red-50", border: "border-red-200", badge: "bg-red-100 text-red-700", label: "失败" },
    cancelled: { bg: "bg-gray-50", border: "border-gray-200", badge: "bg-gray-100 text-gray-500", label: "已取消" },
  }
  return configs[props.task.status]
})

const currentStepIndex = computed(() => {
  if (!props.task.currentStep) return -1
  return STEP_ORDER.indexOf(props.task.currentStep)
})

const stepIndicator = computed(() => {
  if (props.task.status !== "running" || !props.task.currentStep) return null
  const current = currentStepIndex.value + 1
  const total = STEP_ORDER.length
  return `${current}/${total}`
})

const downloadButtonLabel = computed(() =>
  props.task.downloaded ? "重新下载" : "下载"
)

const toggleLogLabel = computed(() =>
  isLogExpanded.value ? "收起日志" : "查看详细日志"
)

function toggleLog(): void {
  isLogExpanded.value = !isLogExpanded.value
}

function download(): void {
  packagerStore.downloadResult(props.task.taskId)
}

function retry(): void {
  packagerStore.retryFailed(props.task.taskId)
}
</script>

<template>
  <div :class="['rounded-lg border p-4', statusConfig?.bg, statusConfig?.border]">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div>
          <div class="font-medium text-gray-900">
            {{ task.name }}
          </div>
          <div class="text-sm text-gray-500">
            {{ task.author }} · v{{ task.version }}
          </div>
        </div>
      </div>
      <span :class="['px-2 py-0.5 rounded text-xs font-medium', statusConfig?.badge]">
        {{ statusConfig?.label }}
      </span>
    </div>

    <div
      v-if="task.status === 'running' && stepIndicator"
      class="mt-2 text-sm text-blue-700"
    >
      步骤 {{ stepIndicator }}：{{ task.stepMessage }}
    </div>

    <div
      v-if="task.status === 'failed' && task.errorMessage"
      class="mt-2 text-sm text-red-600"
    >
      {{ task.errorMessage }}
    </div>

    <div class="mt-2 flex items-center gap-3">
      <button
        v-if="task.status === 'running' || task.status === 'success' || task.status === 'failed'"
        data-testid="toggle-log-btn"
        class="text-sm text-blue-600 hover:text-blue-800"
        @click="toggleLog"
      >
        {{ toggleLogLabel }}
      </button>

      <button
        v-if="task.status === 'success'"
        data-testid="download-btn"
        class="px-3 py-1 text-sm rounded bg-green-600 text-white hover:bg-green-700 transition-colors"
        @click="download"
      >
        {{ downloadButtonLabel }}
      </button>

      <button
        v-if="task.status === 'failed' || task.status === 'cancelled'"
        data-testid="retry-btn"
        class="px-3 py-1 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors"
        @click="retry"
      >
        重新打包
      </button>
    </div>

    <div
      v-if="isLogExpanded"
      class="mt-3 rounded bg-white border border-gray-200 p-3 max-h-48 overflow-y-auto"
    >
      <div
        v-for="(log, index) in task.logs"
        :key="index"
        :class="['text-xs py-0.5', log.isError ? 'text-red-600' : 'text-gray-600']"
      >
        {{ log.message }}
      </div>
      <div
        v-if="task.status === 'failed' && task.rawError"
        class="mt-2 pt-2 border-t border-gray-200 text-xs text-red-800 font-mono whitespace-pre-wrap"
      >
        {{ task.rawError }}
      </div>
    </div>
  </div>
</template>
