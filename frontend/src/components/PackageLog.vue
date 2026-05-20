<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue"
import { usePackagerStore } from "@/stores/packager"
import type { PackTaskProgress, PackStep } from "@/types/packager"
import { STEP_ORDER, getArchitectureLabel } from "@/types/packager"

interface Props {
  task: PackTaskProgress
}
const props = defineProps<Props>()

const packagerStore = usePackagerStore()
const isLogExpanded = ref(false)
const logContainer = ref<HTMLElement | null>(null)
const isAutoScroll = ref(true)

const STEP_SHORT_LABELS: Record<PackStep, string> = {
  downloading: "下载",
  resolving_deps: "解析",
  downloading_deps: "依赖",
  packaging: "打包",
}

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

const progressLabel = computed(() => {
  if (!props.task.progress) return null
  return `${props.task.progress.current}/${props.task.progress.total}`
})

function getStepState(index: number): "completed" | "current" | "pending" | "failed" {
  if (props.task.status === "success") return "completed"
  if (props.task.status === "failed") {
    if (index < currentStepIndex.value) return "completed"
    if (index === currentStepIndex.value) return "failed"
    return "pending"
  }
  if (props.task.status === "cancelled") {
    if (index < currentStepIndex.value) return "completed"
    return "pending"
  }
  if (index < currentStepIndex.value) return "completed"
  if (index === currentStepIndex.value) return "current"
  return "pending"
}

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

function scrollToBottom(): void {
  if (!logContainer.value || !isAutoScroll.value) return
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

function onLogScroll(): void {
  if (!logContainer.value) return
  const { scrollTop, scrollHeight, clientHeight } = logContainer.value
  isAutoScroll.value = scrollHeight - scrollTop - clientHeight < 30
}

watch(() => props.task.status, (newStatus) => {
  if (newStatus === "running") {
    isLogExpanded.value = true
    isAutoScroll.value = true
  } else {
    isAutoScroll.value = false
  }
}, { immediate: true })

watch(() => props.task.logs.length, () => {
  if (props.task.status === "running") {
    scrollToBottom()
  }
})
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
          <div class="text-xs text-gray-400 mt-0.5">
            目标架构: {{ getArchitectureLabel(task.architecture) }}
          </div>
        </div>
      </div>
      <span :class="['px-2 py-0.5 rounded text-xs font-medium', statusConfig?.badge]">
        {{ statusConfig?.label }}
      </span>
    </div>

    <div
      v-if="task.status === 'running' || task.status === 'success' || task.status === 'failed' || task.status === 'cancelled'"
      class="mt-3"
    >
      <div class="flex items-center">
        <template v-for="(step, index) in STEP_ORDER" :key="step">
          <div class="flex flex-col items-center">
            <div
              :class="[
                'w-6 h-6 rounded-full flex items-center justify-center text-xs transition-all duration-300',
                {
                  'bg-green-500 text-white': getStepState(index) === 'completed',
                  'bg-blue-500 text-white animate-pulse': getStepState(index) === 'current',
                  'bg-gray-200 text-gray-400': getStepState(index) === 'pending',
                  'bg-red-500 text-white': getStepState(index) === 'failed',
                }
              ]"
            >
              <svg v-if="getStepState(index) === 'completed'" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              <svg v-else-if="getStepState(index) === 'failed'" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span v-else>{{ index + 1 }}</span>
            </div>
            <span
              :class="[
                'text-[10px] mt-1 whitespace-nowrap',
                {
                  'text-green-600 font-medium': getStepState(index) === 'completed',
                  'text-blue-600 font-medium': getStepState(index) === 'current',
                  'text-gray-400': getStepState(index) === 'pending',
                  'text-red-600 font-medium': getStepState(index) === 'failed',
                }
              ]"
            >
              {{ STEP_SHORT_LABELS[step] }}
            </span>
          </div>
          <div
            v-if="index < STEP_ORDER.length - 1"
            :class="[
              'flex-1 h-0.5 mx-1 mt-[-12px] transition-colors duration-300',
              getStepState(index) === 'completed' ? 'bg-green-400' : 'bg-gray-200'
            ]"
          />
        </template>
      </div>
      <div
        v-if="task.status === 'running' && stepIndicator"
        class="mt-2 text-sm text-blue-700 flex items-center gap-2"
      >
        <span>步骤 {{ stepIndicator }}：{{ task.stepMessage }}</span>
        <span
          v-if="progressLabel"
          class="text-xs bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded font-mono"
        >
          {{ progressLabel }}
        </span>
      </div>
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
      ref="logContainer"
      class="mt-3 rounded bg-white border border-gray-200 p-3 max-h-64 overflow-y-auto"
      @scroll="onLogScroll"
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
