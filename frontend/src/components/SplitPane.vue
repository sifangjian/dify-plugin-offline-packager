<script setup lang="ts">
import { ref } from "vue"

const STORAGE_KEY = "splitpane-left-width"

interface Props {
  defaultLeftWidth?: number
  minLeftWidth?: number
  minRightWidth?: number
}

const props = withDefaults(defineProps<Props>(), {
  defaultLeftWidth: 60,
  minLeftWidth: 30,
  minRightWidth: 25,
})

const emit = defineEmits<{
  resize: [leftWidth: number]
}>()

function clampWidth(width: number): number {
  const maxLeft = 100 - props.minRightWidth
  return Math.min(maxLeft, Math.max(props.minLeftWidth, width))
}

function readSavedWidth(): number {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (!saved) return props.defaultLeftWidth
  const parsed = Number(saved)
  if (isNaN(parsed)) return props.defaultLeftWidth
  return clampWidth(parsed)
}

const leftWidth = ref(readSavedWidth())
const isDragging = ref(false)

function saveWidth(): void {
  localStorage.setItem(STORAGE_KEY, String(leftWidth.value))
}

function onMouseDown(e: MouseEvent): void {
  e.preventDefault()
  isDragging.value = true

  const container = (e.currentTarget as HTMLElement).parentElement
  if (!container) return

  const rect = container.getBoundingClientRect()
  const containerWidth = rect.width

  function onMouseMove(moveEvent: MouseEvent): void {
    const newLeftPercent = ((moveEvent.clientX - rect.left) / containerWidth) * 100
    leftWidth.value = clampWidth(newLeftPercent)
    emit("resize", leftWidth.value)
  }

  function onMouseUp(): void {
    isDragging.value = false
    saveWidth()
    document.removeEventListener("mousemove", onMouseMove)
    document.removeEventListener("mouseup", onMouseUp)
  }

  document.addEventListener("mousemove", onMouseMove)
  document.addEventListener("mouseup", onMouseUp)
}

</script>

<template>
  <div
    data-testid="split-pane"
    class="flex h-full w-full overflow-hidden"
  >
    <div
      data-testid="left-pane"
      :style="{ width: `${leftWidth}%` }"
      class="h-full overflow-auto"
    >
      <slot name="left" />
    </div>
    <div
      data-testid="divider"
      class="w-1 shrink-0 cursor-col-resize bg-gray-200 hover:bg-blue-500 transition-colors"
      @mousedown="onMouseDown"
    />
    <div
      data-testid="right-pane"
      :style="{ width: `${100 - leftWidth}%` }"
      class="h-full overflow-auto"
    >
      <slot name="right" />
    </div>
  </div>
</template>
