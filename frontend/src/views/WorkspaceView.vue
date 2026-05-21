<script setup lang="ts">
import { onMounted } from "vue"
import SplitPane from "@/components/SplitPane.vue"
import SearchPanel from "@/components/SearchPanel.vue"
import TaskPanel from "@/components/TaskPanel.vue"
import { usePackagerStore } from "@/stores/packager"

const packagerStore = usePackagerStore()

onMounted(() => {
  packagerStore.restoreSessions()
})
</script>

<template>
  <div class="h-[calc(100vh-3.5rem)]">
    <SplitPane>
      <template #left>
        <SearchPanel />
      </template>
      <template #right>
        <TaskPanel />
      </template>
    </SplitPane>
  </div>
</template>
