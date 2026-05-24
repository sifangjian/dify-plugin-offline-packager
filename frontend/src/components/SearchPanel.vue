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
import type { UploadResponse } from "@/types/upload"

const emit = defineEmits<{
  pack: [plugin: Plugin]
}>()

const store = useMarketplaceStore()
const packagerStore = usePackagerStore()

const activeTab = ref<"search" | "upload">("search")
const showArchSelector = ref(false)
const pendingPlugin = ref<Plugin | null>(null)
const pendingUploadedPlugin = ref<UploadResponse | null>(null)

const isDragging = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

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
  if (pendingUploadedPlugin.value) {
    packagerStore.setArchitecture(architecture)
    packagerStore.packUploadedPlugin(pendingUploadedPlugin.value, architecture)
    pendingUploadedPlugin.value = null
    return
  }
  if (!pendingPlugin.value) return
  packagerStore.setArchitecture(architecture)
  packagerStore.enqueuePlugin(pendingPlugin.value)
  packagerStore.dequeueAndPack(architecture)
  emit("pack", pendingPlugin.value)
  pendingPlugin.value = null
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  isDragging.value = true
}

function handleDragLeave() {
  isDragging.value = false
}

async function handleDrop(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
  const files = Array.from(e.dataTransfer?.files || []).filter(
    (f) => f.name.endsWith(".difypkg"),
  )
  if (files.length === 0) return
  await doUpload(files)
}

function openFilePicker() {
  fileInputRef.value?.click()
}

async function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (files.length === 0) return
  await doUpload(files)
  input.value = ""
}

async function doUpload(files: File[]) {
  await packagerStore.uploadLocalFiles(files)
}

function onUploadedPackClick(plugin: UploadResponse) {
  pendingUploadedPlugin.value = plugin
  showArchSelector.value = true
}

function getPluginLabel(plugin: UploadResponse): string {
  return plugin.label.zh_Hans || plugin.label.en_US || plugin.name
}

function getPluginDescription(plugin: UploadResponse): string {
  return plugin.description.zh_Hans || plugin.description.en_US || ""
}

function isPluginPacked(uploadId: string): boolean {
  return packagerStore.isUploadedPluginInQueue(uploadId)
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
        <div
          class="border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer"
          :class="isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'"
          @dragover="handleDragOver"
          @dragleave="handleDragLeave"
          @drop="handleDrop"
          @click="openFilePicker"
        >
          <template v-if="packagerStore.isUploading">
            <div class="flex items-center justify-center gap-2">
              <svg
                class="animate-spin h-5 w-5 text-blue-500"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                />
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              <span class="text-blue-600">上传解析中...</span>
            </div>
          </template>
          <template v-else>
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
              拖拽 .difypkg 文件到此处，或点击选择文件
            </p>
          </template>
          <input
            ref="fileInputRef"
            type="file"
            accept=".difypkg"
            multiple
            class="hidden"
            @change="handleFileSelect"
          >
        </div>

        <div
          v-if="packagerStore.uploadErrors.length > 0"
          class="mt-4 space-y-2"
        >
          <div
            v-for="error in packagerStore.uploadErrors"
            :key="error.filename"
            class="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between"
          >
            <div>
              <span class="font-medium text-sm">{{ error.filename }}</span>
              <span class="text-red-600 text-sm ml-2">{{ error.error }}</span>
            </div>
            <button
              class="text-gray-400 hover:text-gray-600"
              @click="packagerStore.clearUploadErrors()"
            >
              <svg
                class="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        <div
          v-if="packagerStore.uploadedPlugins.length > 0"
          class="mt-4 space-y-3"
        >
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-medium text-gray-700">
              已上传插件 ({{ packagerStore.uploadedPlugins.length }})
            </h3>
            <button
              class="text-xs text-gray-400 hover:text-red-500"
              @click="() => { packagerStore.uploadedPlugins.splice(0) }"
            >
              清空
            </button>
          </div>
          <div
            v-for="plugin in packagerStore.uploadedPlugins"
            :key="plugin.upload_id"
            class="p-3 border border-gray-200 rounded-lg bg-white"
          >
            <div class="flex items-center justify-between gap-3">
              <div class="flex-1 min-w-0">
                <p class="font-medium text-sm truncate">
                  {{ getPluginLabel(plugin) }}
                </p>
                <p class="text-xs text-gray-500 mt-0.5">
                  {{ plugin.author }} · v{{ plugin.version }}
                </p>
                <p
                  v-if="getPluginDescription(plugin)"
                  class="text-xs text-gray-400 mt-1 truncate"
                >
                  {{ getPluginDescription(plugin) }}
                </p>
              </div>
              <button
                class="shrink-0 px-3 py-1.5 text-xs font-medium rounded-md transition-colors"
                :class="isPluginPacked(plugin.upload_id)
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-500 text-white hover:bg-blue-600'"
                :disabled="isPluginPacked(plugin.upload_id)"
                @click.stop="onUploadedPackClick(plugin)"
              >
                {{ isPluginPacked(plugin.upload_id) ? '打包中' : '打包' }}
              </button>
            </div>
          </div>
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
