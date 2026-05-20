<script setup lang="ts">
import { ref, watch } from "vue"
import { ARCHITECTURE_OPTIONS } from "@/types/packager"
import type { Architecture } from "@/types/packager"

interface Props {
  modelValue: boolean
  selectedArchitecture: Architecture
}

const props = defineProps<Props>()
const emit = defineEmits<{
  "update:modelValue": [value: boolean]
  confirm: [architecture: Architecture]
}>()

const selectedArch = ref<Architecture>(props.selectedArchitecture)

watch(
  () => props.selectedArchitecture,
  (val) => {
    selectedArch.value = val
  },
)

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      selectedArch.value = props.selectedArchitecture
    }
  },
)

function selectArchitecture(arch: Architecture): void {
  selectedArch.value = arch
}

function confirm(): void {
  emit("confirm", selectedArch.value)
  emit("update:modelValue", false)
}

function cancel(): void {
  emit("update:modelValue", false)
}
</script>

<template>
  <div v-if="modelValue" data-testid="arch-selector">
    <div
      data-testid="arch-overlay"
      class="fixed inset-0 z-50 bg-black/50"
    />
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-md p-6" @click.stop>
        <h3 class="text-lg font-semibold text-gray-900 mb-4">
          选择目标架构
        </h3>

        <div class="flex flex-col gap-2">
          <div
            v-for="option in ARCHITECTURE_OPTIONS"
            :key="option.value"
            :data-testid="`arch-option-${option.value}`"
            :class="[
              'flex items-center gap-3 p-3 rounded-lg border-2 cursor-pointer transition-all',
              selectedArch === option.value
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
            ]"
            @click="selectArchitecture(option.value)"
          >
            <div
              :class="[
                'w-4 h-4 rounded-full border-2 flex items-center justify-center',
                selectedArch === option.value
                  ? 'border-blue-500'
                  : 'border-gray-300'
              ]"
            >
              <div
                v-if="selectedArch === option.value"
                class="w-2 h-2 rounded-full bg-blue-500"
              />
            </div>
            <div>
              <div class="font-medium text-gray-900">
                {{ option.label }}
              </div>
              <div class="text-sm text-gray-500">
                {{ option.description }}
              </div>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-6">
          <button
            data-testid="arch-cancel-btn"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            @click="cancel"
          >
            取消
          </button>
          <button
            data-testid="arch-confirm-btn"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            @click="confirm"
          >
            确认
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
