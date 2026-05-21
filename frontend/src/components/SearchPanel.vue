<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue"
import { useMarketplaceStore } from "@/stores/marketplace"
import { usePackagerStore } from "@/stores/packager"
import PluginCard from "@/components/PluginCard.vue"
import PluginCardSkeleton from "@/components/PluginCardSkeleton.vue"
import CategoryFilter from "@/components/CategoryFilter.vue"
import ArchitectureSelector from "@/components/ArchitectureSelector.vue"
import type { Plugin } from "@/types/marketplace"
import type { Architecture } from "@/types/packager"

const emit = defineEmits<{
  pack: [plugin: Plugin]
}>()

const store = useMarketplaceStore()
const packagerStore = usePackagerStore()

const activeTab = ref<"search" | "upload">("search")
const showArchSelector = ref(false)
const pendingPlugin = ref<Plugin | null>(null)

const sentinelRef = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

function handleCategoryChange(value: string) {
  if (value === store.category) {
    store.clearCategory()
  } else {
    store.setCategory(value)
  }
}

function onPackClick(plugin: Plugin) {
  pendingPlugin.value = plugin
  showArchSelector.value = true
}

function onArchConfirm(architecture: Architecture) {
  showArchSelector.value = false
  if (!pendingPlugin.value) return
  packagerStore.setArchitecture(architecture)
  packagerStore.enqueuePlugin(pendingPlugin.value)
  packagerStore.dequeueAndPack(architecture)
  emit("pack", pendingPlugin.value)
  pendingPlugin.value = null
}

onMounted(() => {
  store.search()

  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting && store.hasMore && !store.isLoading) {
        store.loadMore()
      }
    },
    { rootMargin: "200px" },
  )

  if (sentinelRef.value) {
    observer.observe(sentinelRef.value)
  }
})

onUnmounted(() => {
  observer?.disconnect()
})
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="flex border-b border-gray-200">
      <button
        data-testid="tab-search"
        :class="[
          'flex-1 py-2.5 text-sm font-medium text-center border-b-2 transition-colors',
          activeTab === 'search'
            ? 'text-blue-600 border-blue-600'
            : 'text-gray-500 border-transparent hover:text-gray-700'
        ]"
        @click="activeTab = 'search'"
      >
        在线搜索
      </button>
      <button
        data-testid="tab-upload"
        :class="[
          'flex-1 py-2.5 text-sm font-medium text-center border-b-2 transition-colors',
          activeTab === 'upload'
            ? 'text-blue-600 border-blue-600'
            : 'text-gray-500 border-transparent hover:text-gray-700'
        ]"
        @click="activeTab = 'upload'"
      >
        本地上传
      </button>
    </div>

    <div class="flex-1 overflow-y-auto">
      <div
        v-if="activeTab === 'search'"
        data-testid="search-content"
      >
        <div class="sticky top-0 z-10 bg-white px-4 py-3">
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

        <div class="px-4 py-2">
          <CategoryFilter
            :category="store.category"
            @update:category="handleCategoryChange"
          />
        </div>

        <div class="px-4 py-4">
          <div
            v-if="store.isLoading && store.plugins.length === 0"
            class="grid grid-cols-2 gap-4"
          >
            <PluginCardSkeleton
              v-for="i in 6"
              :key="i"
            />
          </div>

          <div
            v-else-if="store.error"
            class="text-center py-16"
          >
            <p class="text-gray-500">
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
            <p class="text-gray-400">
              未找到匹配的插件，请尝试其他关键词或分类
            </p>
          </div>

          <div v-else>
            <div class="grid grid-cols-2 gap-4">
              <PluginCard
                v-for="plugin in store.plugins"
                :key="plugin.plugin_id"
                :plugin="plugin"
                @pack="onPackClick"
              />
            </div>

            <div
              v-if="store.isLoading && store.plugins.length > 0"
              class="grid grid-cols-2 gap-4 mt-4"
            >
              <PluginCardSkeleton
                v-for="i in 3"
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

      <div
        v-if="activeTab === 'upload'"
        data-testid="upload-content"
        class="p-4"
      >
        <div class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors">
          <svg
            class="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.5"
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <p class="mt-2 text-sm text-gray-600">
            拖拽 .difypkg 文件到此处，或点击上传
          </p>
          <input
            type="file"
            accept=".difypkg"
            class="hidden"
          >
        </div>
      </div>
    </div>

    <ArchitectureSelector
      v-model="showArchSelector"
      :selected-architecture="packagerStore.selectedArchitecture"
      @confirm="onArchConfirm"
    />
  </div>
</template>
