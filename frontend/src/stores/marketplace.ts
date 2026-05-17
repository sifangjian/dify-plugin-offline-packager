import { defineStore } from "pinia"
import { ref, computed } from "vue"
import { searchPlugins } from "@/api/marketplace"
import type { Plugin, ApiError } from "@/types/marketplace"

const PAGE_SIZE = 20

export const useMarketplaceStore = defineStore("marketplace", () => {
  const keyword = ref("")
  const category = ref("")
  const plugins = ref<Plugin[]>([])
  const total = ref(0)
  const currentPage = ref(1)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const hasMore = computed(() => plugins.value.length < total.value)

  let abortController: AbortController | null = null

  async function search() {
    abortController?.abort()
    abortController = new AbortController()
    const currentController = abortController

    currentPage.value = 1
    plugins.value = []
    isLoading.value = true
    error.value = null

    try {
      const result = await searchPlugins(
        {
          keyword: keyword.value,
          category: category.value,
          page: 1,
          page_size: PAGE_SIZE,
        },
        currentController.signal,
      )
      if (currentController !== abortController) return
      plugins.value = result.plugins
      total.value = result.total
    } catch (err) {
      if (currentController !== abortController) return
      if (err instanceof DOMException && err.name === "CanceledError") return
      const apiError = err as ApiError
      error.value = apiError.message || "搜索失败，请稍后重试"
    } finally {
      if (currentController === abortController) {
        isLoading.value = false
      }
    }
  }

  async function loadMore() {
    if (isLoading.value || !hasMore.value) return

    abortController?.abort()
    abortController = new AbortController()
    const currentController = abortController

    const nextPage = currentPage.value + 1
    isLoading.value = true
    error.value = null

    try {
      const result = await searchPlugins(
        {
          keyword: keyword.value,
          category: category.value,
          page: nextPage,
          page_size: PAGE_SIZE,
        },
        currentController.signal,
      )
      if (currentController !== abortController) return
      plugins.value.push(...result.plugins)
      total.value = result.total
      currentPage.value = nextPage
    } catch (err) {
      if (currentController !== abortController) return
      if (err instanceof DOMException && err.name === "CanceledError") return
      const apiError = err as ApiError
      error.value = apiError.message || "加载失败，请稍后重试"
    } finally {
      if (currentController === abortController) {
        isLoading.value = false
      }
    }
  }

  function setKeyword(value: string) {
    keyword.value = value
  }

  function setCategory(value: string) {
    category.value = value
    search()
  }

  function clearCategory() {
    category.value = ""
    search()
  }

  return {
    keyword,
    category,
    plugins,
    total,
    currentPage,
    isLoading,
    error,
    hasMore,
    search,
    loadMore,
    setKeyword,
    setCategory,
    clearCategory,
  }
})
