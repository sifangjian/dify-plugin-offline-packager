<template>
  <div class="min-h-screen bg-gray-50">
    <header class="sticky top-0 z-10 bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 py-3">
        <div class="flex gap-2">
          <input
            v-model="store.keyword"
            type="text"
            placeholder="搜索插件..."
            class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            @keyup.enter="store.search()"
          >
          <button
            class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            @click="store.search()"
          >
            搜索
          </button>
        </div>
      </div>
    </header>

    <div class="max-w-7xl mx-auto px-4 py-2">
      <CategoryFilter
        :category="store.category"
        @update:category="handleCategoryChange"
      />
    </div>

    <div class="max-w-7xl mx-auto px-4 py-4">
      <div
        v-if="store.isLoading && store.plugins.length === 0"
        class="grid grid-cols-4 gap-4"
      >
        <PluginCardSkeleton
          v-for="i in 8"
          :key="i"
        />
      </div>

      <div
        v-else-if="store.error"
        class="text-center py-16"
      >
        <svg
          class="mx-auto h-12 w-12 text-red-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
          />
        </svg>
        <p class="mt-4 text-gray-500">
          {{ store.error }}
        </p>
        <button
          class="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          @click="store.search()"
        >
          重试
        </button>
      </div>

      <div
        v-else-if="store.plugins.length === 0 && !store.isLoading"
        class="text-center py-16"
      >
        <svg
          class="mx-auto h-12 w-12 text-gray-300"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <p class="mt-4 text-gray-400">
          未找到匹配的插件，请尝试其他关键词或分类
        </p>
      </div>

      <div v-else>
        <div class="grid grid-cols-4 gap-4">
          <PluginCard
            v-for="plugin in store.plugins"
            :key="plugin.plugin_id"
            :plugin="plugin"
          />
        </div>

        <div
          v-if="store.isLoading && store.plugins.length > 0"
          class="grid grid-cols-4 gap-4 mt-4"
        >
          <PluginCardSkeleton
            v-for="i in 4"
            :key="`more-${i}`"
          />
        </div>

        <p
          v-if="!store.hasMore && store.plugins.length > 0"
          class="text-center py-4 text-gray-400"
        >
          没有更多了
        </p>
      </div>
    </div>

    <div
      ref="sentinelRef"
      class="h-1"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue"
import { useMarketplaceStore } from "@/stores/marketplace"
import PluginCard from "@/components/PluginCard.vue"
import PluginCardSkeleton from "@/components/PluginCardSkeleton.vue"
import CategoryFilter from "@/components/CategoryFilter.vue"

const store = useMarketplaceStore()
const sentinelRef = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

function handleCategoryChange(value: string) {
  if (value === store.category) {
    store.clearCategory()
  } else {
    store.setCategory(value)
  }
}

onMounted(() => {
  store.search()

  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting && store.hasMore && !store.isLoading) {
        store.loadMore()
      }
    },
    { rootMargin: "200px" }
  )

  if (sentinelRef.value) {
    observer.observe(sentinelRef.value)
  }
})

onUnmounted(() => {
  observer?.disconnect()
})
</script>
