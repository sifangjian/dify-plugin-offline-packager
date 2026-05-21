<script setup lang="ts">
import { computed } from "vue"
import { usePackagerStore } from "@/stores/packager"

const packagerStore = usePackagerStore()

const taskCount = computed(() => packagerStore.taskList.length)
</script>

<template>
  <header class="fixed top-0 left-0 right-0 z-30 h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4">
    <h1 class="text-lg font-semibold text-gray-900">
      Dify Plugin Offline Packager
    </h1>
    <div class="relative">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="w-6 h-6 text-gray-600"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
        />
      </svg>
      <span
        v-if="taskCount > 0"
        data-testid="task-badge"
        :class="[
          'absolute -top-1 -right-1 min-w-5 h-5 flex items-center justify-center rounded-full bg-blue-600 text-white text-xs font-medium px-1',
          packagerStore.isPacking ? 'animate-pulse' : ''
        ]"
      >
        {{ taskCount }}
      </span>
    </div>
  </header>
</template>
