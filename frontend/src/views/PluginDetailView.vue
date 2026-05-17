<template>
  <div class="min-h-screen bg-gray-50">
    <header class="sticky top-0 z-10 bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
        <button
          class="text-gray-500 hover:text-gray-700 transition-colors"
          @click="router.back()"
        >
          <svg
            class="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>
        <h1 class="text-lg font-medium">
          插件详情
        </h1>
      </div>
    </header>

    <div
      v-if="isLoading"
      class="max-w-7xl mx-auto px-4 py-8"
    >
      <div class="animate-pulse">
        <div class="h-8 bg-gray-200 rounded w-1/3 mb-4" />
        <div class="h-4 bg-gray-200 rounded w-1/2 mb-8" />
        <div class="h-32 bg-gray-200 rounded" />
      </div>
    </div>

    <div
      v-else-if="error"
      class="max-w-7xl mx-auto px-4 py-16 text-center"
    >
      <p class="text-gray-500">
        {{ error }}
      </p>
      <button
        class="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
        @click="fetchDetail"
      >
        重试
      </button>
    </div>

    <div
      v-else-if="plugin"
      class="max-w-7xl mx-auto px-4 py-6"
    >
      <div class="bg-white rounded-lg border p-6">
        <div class="flex items-start gap-4">
          <div class="flex-1 min-w-0">
            <h2 class="text-xl font-semibold">
              {{ getI18nText(plugin.label) }}
            </h2>
            <p class="text-sm text-gray-500 mt-1">
              {{ plugin.org }}
            </p>
            <div class="flex items-center gap-3 mt-2">
              <span
                v-if="plugin.category"
                class="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded"
              >
                {{ plugin.category }}
              </span>
              <span class="text-xs text-gray-400">
                {{ formatInstallCount(plugin.install_count) }} 次安装
              </span>
              <span
                v-if="plugin.latest_version"
                class="text-xs text-gray-400"
              >
                v{{ plugin.latest_version }}
              </span>
            </div>
          </div>
          <button
            :disabled="cartStore.hasItem(plugin.plugin_id)"
            :class="cartStore.hasItem(plugin.plugin_id)
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-500 text-white hover:bg-blue-600'"
            class="px-4 py-2 text-sm rounded-lg transition-colors shrink-0"
            @click="cartStore.addItem(plugin)"
          >
            {{ cartStore.hasItem(plugin.plugin_id) ? '已添加' : '添加' }}
          </button>
        </div>

        <div
          v-if="plugin.introduction"
          class="mt-6"
        >
          <h3 class="text-sm font-medium text-gray-700 mb-2">
            介绍
          </h3>
          <div
            class="markdown-body text-sm text-gray-600"
            v-html="renderedIntroduction"
          />
        </div>

        <div
          v-if="plugin.tags && plugin.tags.length > 0"
          class="mt-6"
        >
          <h3 class="text-sm font-medium text-gray-700 mb-2">
            标签
          </h3>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="tag in plugin.tags"
              :key="tag"
              class="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded"
            >
              {{ tag }}
            </span>
          </div>
        </div>

        <div class="mt-6 grid grid-cols-2 gap-4 text-sm">
          <div v-if="plugin.repository">
            <span class="text-gray-500">仓库：</span>
            <a
              :href="plugin.repository"
              target="_blank"
              class="text-blue-500 hover:underline"
            >
              {{ plugin.repository }}
            </a>
          </div>
          <div v-if="plugin.privacy_policy">
            <span class="text-gray-500">隐私政策：</span>
            <a
              :href="plugin.privacy_policy"
              target="_blank"
              class="text-blue-500 hover:underline"
            >
              {{ plugin.privacy_policy }}
            </a>
          </div>
          <div v-if="plugin.resource">
            <span class="text-gray-500">内存需求：</span>
            <span>{{ plugin.resource.memory }} MB</span>
          </div>
          <div v-if="plugin.updated_at">
            <span class="text-gray-500">更新时间：</span>
            <span>{{ plugin.updated_at }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { useRoute, useRouter } from "vue-router"
import { marked } from "marked"
import DOMPurify from "dompurify"
import { getPluginDetail } from "@/api/marketplace"
import { useCartStore } from "@/stores/cart"
import type { Plugin } from "@/types/marketplace"

const route = useRoute()
const router = useRouter()
const cartStore = useCartStore()

const plugin = ref<Plugin | null>(null)
const isLoading = ref(true)
const error = ref<string | null>(null)

const renderedIntroduction = computed(() => {
  if (!plugin.value?.introduction) return ""
  const rawHtml = marked.parse(plugin.value.introduction) as string
  return DOMPurify.sanitize(rawHtml)
})

function getI18nText(text: { zh_Hans: string; en_US: string }): string {
  return text.zh_Hans || text.en_US
}

function formatInstallCount(count: number): string {
  if (count >= 10000) return `${(count / 10000).toFixed(1)}万`
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`
  return String(count)
}

async function fetchDetail() {
  const author = route.params.author as string
  const name = route.params.name as string
  if (!author || !name) return

  isLoading.value = true
  error.value = null

  try {
    plugin.value = await getPluginDetail(author, name)
  } catch (err: unknown) {
    const apiError = err as { message?: string }
    error.value = apiError.message || "加载插件详情失败"
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchDetail)
</script>

<style scoped>
.markdown-body :deep(h1) {
  font-size: 1.5em;
  font-weight: 600;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  line-height: 1.3;
}

.markdown-body :deep(h2) {
  font-size: 1.25em;
  font-weight: 600;
  margin-top: 1.25em;
  margin-bottom: 0.5em;
  line-height: 1.3;
}

.markdown-body :deep(h3) {
  font-size: 1.1em;
  font-weight: 600;
  margin-top: 1em;
  margin-bottom: 0.5em;
  line-height: 1.3;
}

.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  font-size: 1em;
  font-weight: 600;
  margin-top: 1em;
  margin-bottom: 0.5em;
}

.markdown-body :deep(p) {
  margin-top: 0;
  margin-bottom: 0.75em;
  line-height: 1.6;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin-top: 0;
  margin-bottom: 0.75em;
  padding-left: 1.5em;
}

.markdown-body :deep(ul) {
  list-style-type: disc;
}

.markdown-body :deep(ol) {
  list-style-type: decimal;
}

.markdown-body :deep(li) {
  margin-top: 0.25em;
  margin-bottom: 0.25em;
  line-height: 1.6;
}

.markdown-body :deep(li > ul),
.markdown-body :deep(li > ol) {
  margin-top: 0.25em;
  margin-bottom: 0;
}

.markdown-body :deep(code) {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  font-size: 0.875em;
  background-color: rgba(0, 0, 0, 0.06);
  border-radius: 0.25em;
  padding: 0.15em 0.35em;
}

.markdown-body :deep(pre) {
  margin-top: 0;
  margin-bottom: 0.75em;
  background-color: #1e1e2e;
  border-radius: 0.5em;
  padding: 1em;
  overflow-x: auto;
}

.markdown-body :deep(pre code) {
  background: none;
  border-radius: 0;
  padding: 0;
  font-size: 0.85em;
  color: #cdd6f4;
}

.markdown-body :deep(blockquote) {
  margin-top: 0;
  margin-bottom: 0.75em;
  padding: 0.5em 1em;
  border-left: 3px solid #d1d5db;
  background-color: rgba(0, 0, 0, 0.03);
  color: #4b5563;
}

.markdown-body :deep(blockquote p) {
  margin-bottom: 0;
}

.markdown-body :deep(a) {
  color: #3b82f6;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 1.5em 0;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-top: 0;
  margin-bottom: 0.75em;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 0.5em 0.75em;
  text-align: left;
}

.markdown-body :deep(th) {
  background-color: #f9fafb;
  font-weight: 600;
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 0.5em;
}
</style>
