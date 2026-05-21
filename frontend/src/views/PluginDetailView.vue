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
                {{ getCategoryLabel(plugin.category) }}
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
            :disabled="packagerStore.isInQueue(plugin.plugin_id)"
            :class="packagerStore.isInQueue(plugin.plugin_id)
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-500 text-white hover:bg-blue-600'"
            class="px-4 py-2 text-sm rounded-lg transition-colors shrink-0"
            @click="onPackClick"
          >
            {{ packagerStore.isInQueue(plugin.plugin_id) ? '打包中' : '打包' }}
          </button>
        </div>

        <div
          v-if="displayIntroduction"
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
              :key="tag.name"
              :title="getTagTooltip(tag.name)"
              class="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded cursor-help"
            >
              {{ getTagLabel(tag.name) }}
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
            <span>{{ formatMemory(plugin.resource.memory) }}</span>
          </div>
          <div v-if="plugin.updated_at">
            <span class="text-gray-500">更新时间：</span>
            <span>{{ formatDateTime(plugin.updated_at) }}</span>
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

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { useRoute, useRouter } from "vue-router"
import { marked } from "marked"
import DOMPurify from "dompurify"
import { getPluginDetail } from "@/api/marketplace"
import { usePackagerStore } from "@/stores/packager"
import ArchitectureSelector from "@/components/ArchitectureSelector.vue"
import type { Plugin } from "@/types/marketplace"
import type { Architecture } from "@/types/packager"

const TAG_LABELS: Record<string, string> = {
  agent: "Agent 策略",
  tool: "工具",
  model: "模型",
  llm: "大语言模型",
  text_embedding: "文本嵌入",
  rerank: "重排序",
  tts: "文本转语音",
  speech2text: "语音转文本",
  extension: "扩展",
  endpoint: "端点",
  datasource: "数据源",
  trigger: "触发器",
  productivity: "生产力",
  search: "搜索",
  communication: "通讯",
  image: "图像",
  audio: "音频",
  video: "视频",
  coding: "编程",
  data: "数据",
  security: "安全",
  analytics: "分析",
  automation: "自动化",
}

const TAG_TOOLTIPS: Record<string, string> = {
  agent: "Agent 推理策略插件，定义 Agent 节点中的工具选择和调用逻辑",
  tool: "工具类插件，提供外部 API 调用能力，可在工作流或 Agent 中使用",
  model: "模型类插件，集成大语言模型或其他 AI 模型的调用能力",
  llm: "大语言模型插件，支持文本生成、对话等核心语言能力",
  text_embedding: "文本嵌入插件，将文本转换为向量表示，用于语义搜索和相似度计算",
  rerank: "重排序插件，对搜索结果进行相关性重新排序，提升检索精度",
  tts: "文本转语音插件，将文本内容转换为语音输出",
  speech2text: "语音转文本插件，将语音输入转换为文字内容",
  extension: "扩展类插件，提供轻量级的 HTTP 端点服务",
  endpoint: "端点插件，注册自定义 HTTP 接口，支持 Webhook 等场景",
  datasource: "数据源插件，从外部系统导入数据到知识库",
  trigger: "触发器插件，基于事件驱动工作流执行",
  productivity: "生产力工具，提升工作效率的插件",
  search: "搜索工具，提供信息检索和查询能力",
  communication: "通讯工具，支持消息发送和接收",
  image: "图像处理工具，支持图像生成、编辑和分析",
  audio: "音频处理工具，支持音频相关操作",
  video: "视频处理工具，支持视频相关操作",
  coding: "编程工具，支持代码生成、分析和执行",
  data: "数据处理工具，支持数据转换、清洗和管理",
  security: "安全工具，提供内容审核和安全检测能力",
  analytics: "分析工具，提供数据分析和洞察功能",
  automation: "自动化工具，支持任务自动执行和流程编排",
}

const CATEGORY_LABELS: Record<string, string> = {
  model: "模型",
  tool: "工具",
  "agent-strategy": "Agent 策略",
  extension: "扩展",
  bundle: "插件包",
  datasource: "数据源",
  trigger: "触发器",
}

const route = useRoute()
const router = useRouter()
const packagerStore = usePackagerStore()

const plugin = ref<Plugin | null>(null)
const localizedIntroduction = ref<string>("")
const isLoading = ref(true)
const error = ref<string | null>(null)
const showArchSelector = ref(false)

const displayIntroduction = computed(() => {
  return localizedIntroduction.value || plugin.value?.introduction || ""
})

const renderedIntroduction = computed(() => {
  const content = displayIntroduction.value
  if (!content) return ""
  const rawHtml = marked.parse(content) as string
  return DOMPurify.sanitize(rawHtml)
})

function onPackClick() {
  showArchSelector.value = true
}

function onArchConfirm(architecture: Architecture) {
  showArchSelector.value = false
  if (!plugin.value) return
  packagerStore.setArchitecture(architecture)
  packagerStore.enqueuePlugin(plugin.value)
  packagerStore.dequeueAndPack(architecture)
}

function getI18nText(text: { zh_Hans: string; en_US: string }): string {
  return text.zh_Hans || text.en_US
}

function getTagLabel(tagName: string): string {
  return TAG_LABELS[tagName] || tagName
}

function getTagTooltip(tagName: string): string {
  return TAG_TOOLTIPS[tagName] || `标签：${tagName}`
}

function getCategoryLabel(category: string): string {
  return CATEGORY_LABELS[category] || category
}

function formatInstallCount(count: number): string {
  if (count >= 10000) return `${(count / 10000).toFixed(1)}万`
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`
  return String(count)
}

function formatMemory(bytes: number): string {
  if (bytes <= 0) return "0 MB"
  const mb = bytes / (1024 * 1024)
  if (mb < 1) return `${bytes} B`
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`
  if (Number.isInteger(mb)) return `${mb} MB`
  return `${mb.toFixed(1)} MB`
}

function formatDateTime(dateStr: string): string {
  if (!dateStr) return ""
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return dateStr
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  const hours = String(date.getHours()).padStart(2, "0")
  const minutes = String(date.getMinutes()).padStart(2, "0")
  return `${year}年${month}月${day}日 ${hours}:${minutes}`
}

async function fetchLocalizedIntroduction(author: string, name: string) {
  if (!plugin.value?.readme_meta?.available_languages) return
  const hasZhHans = plugin.value.readme_meta.available_languages.includes("zh_Hans")
  if (!hasZhHans) return

  try {
    const zhPlugin = await getPluginDetail(author, name, "zh_Hans")
    if (zhPlugin.introduction && zhPlugin.introduction.trim()) {
      localizedIntroduction.value = zhPlugin.introduction
    }
  } catch {
    localizedIntroduction.value = ""
  }
}

async function fetchDetail() {
  const author = route.params.author as string
  const name = route.params.name as string
  if (!author || !name) return

  isLoading.value = true
  error.value = null
  localizedIntroduction.value = ""

  try {
    plugin.value = await getPluginDetail(author, name)
    await fetchLocalizedIntroduction(author, name)
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
