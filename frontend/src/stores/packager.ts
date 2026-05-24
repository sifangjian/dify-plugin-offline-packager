import { defineStore } from "pinia"
import { ref, computed } from "vue"
import { useSSE } from "@/composables/useSSE"
import { startPack, cancelSession, getDownloadUrl, uploadPlugins } from "@/api/plugin"
import type {
  Architecture,
  PackPluginItem,
  PackResponse,
  PackTaskProgress,
  SSEEvent,
} from "@/types/packager"
import { ARCHITECTURE_OPTIONS } from "@/types/packager"
import type { Plugin } from "@/types/marketplace"
import type { UploadResponse, UploadError, BatchUploadResponse } from "@/types/upload"

const PACKAGER_STORAGE_KEY = "dify-plugin-packager"
const QUEUE_STORAGE_KEY = "dify-plugin-packager-queue"

interface SessionState {
  sessionId: string
  taskIds: string[]
  completed: boolean
}

function saveToStorage(sessions: Map<string, SessionState>, tasks: Map<string, PackTaskProgress>): void {
  const data = {
    sessions: Array.from(sessions.values()),
    tasks: Array.from(tasks.values()),
  }
  sessionStorage.setItem(PACKAGER_STORAGE_KEY, JSON.stringify(data))
}

function loadFromStorage(): { sessions: Map<string, SessionState>; tasks: Map<string, PackTaskProgress> } {
  const raw = sessionStorage.getItem(PACKAGER_STORAGE_KEY)
  if (!raw) return { sessions: new Map(), tasks: new Map() }
  try {
    const data = JSON.parse(raw)
    const sessions: Map<string, SessionState> = new Map(
      data.sessions.map((s: SessionState) => [s.sessionId, s] as [string, SessionState]),
    )
    const tasks: Map<string, PackTaskProgress> = new Map(
      data.tasks.map((t: PackTaskProgress) => [t.taskId, t] as [string, PackTaskProgress]),
    )
    return { sessions, tasks }
  } catch {
    return { sessions: new Map(), tasks: new Map() }
  }
}

function loadQueueFromStorage(): Plugin[] {
  const raw = sessionStorage.getItem(QUEUE_STORAGE_KEY)
  if (!raw) return []
  try {
    return JSON.parse(raw) as Plugin[]
  } catch {
    return []
  }
}

function saveQueueToStorage(items: Plugin[]): void {
  sessionStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(items))
}

export const usePackagerStore = defineStore("packager", () => {
  const persisted = loadFromStorage()
  const sessions = ref(persisted.sessions)
  const tasks = ref(persisted.tasks)
  const connectionError = ref<string | null>(null)
  const selectedArchitecture = ref<Architecture>("linux-amd64")
  const queuedItems = ref<Plugin[]>(loadQueueFromStorage())
  const uploadedPlugins = ref<UploadResponse[]>([])
  const uploadErrors = ref<UploadError[]>([])
  const isUploading = ref(false)

  const sseConnections = new Map<string, ReturnType<typeof useSSE>>()

  const isPacking = computed(() => {
    for (const task of tasks.value.values()) {
      if (task.status === "pending" || task.status === "running") {
        return true
      }
    }
    return false
  })

  const taskList = computed(() => Array.from(tasks.value.values()))

  const hasTasks = computed(() => tasks.value.size > 0)

  function persistState(): void {
    saveToStorage(sessions.value, tasks.value)
  }

  function handleSSEEvent(event: SSEEvent): void {
    switch (event.event_type) {
      case "session_started":
        break

      case "task_started": {
        const task = tasks.value.get(event.task_id)
        if (task) {
          task.status = "running"
          task.currentStep = null
          task.stepMessage = null
        }
        break
      }

      case "step_progress": {
        const task = tasks.value.get(event.task_id)
        if (task) {
          task.status = "running"
          task.currentStep = event.step
          task.stepMessage = event.message
          task.stepDetail = event.detail || null
          task.progress = event.progress || null
          task.logs.push({
            step: event.step,
            message: event.detail || event.message,
            timestamp: event.timestamp,
          })
          if (task.logs.length > 200) {
            task.logs.splice(0, task.logs.length - 200)
          }
        }
        break
      }

      case "task_success": {
        const task = tasks.value.get(event.task_id)
        if (task) {
          task.status = "success"
          task.currentStep = null
          task.stepMessage = "打包完成"
          task.logs.push({
            step: "packaging" as const,
            message: "打包完成",
            timestamp: event.timestamp,
          })
        }
        break
      }

      case "task_failed": {
        const task = tasks.value.get(event.task_id)
        if (task) {
          task.status = "failed"
          task.errorMessage = event.message
          task.rawError = event.raw_error
          task.logs.push({
            step: event.step,
            message: event.message,
            timestamp: event.timestamp,
            isError: true,
          })
        }
        break
      }

      case "session_completed": {
        const session = sessions.value.get(event.session_id)
        if (session) {
          session.completed = true
        }
        disconnectSSE(event.session_id)
        break
      }
    }

    persistState()
  }

  function connectSSE(sessionId: string): void {
    if (sseConnections.has(sessionId)) return

    const sse = useSSE({
      onEvent: handleSSEEvent,
      onError: () => {
        connectionError.value = "连接已断开，打包可能仍在后台进行，请刷新页面查看"
      },
      onNotFound: () => {
        const session = sessions.value.get(sessionId)
        if (session) {
          session.completed = true
        }
        for (const taskId of session?.taskIds || []) {
          const task = tasks.value.get(taskId)
          if (task && (task.status === "pending" || task.status === "running")) {
            task.status = "failed"
            task.errorMessage = "会话不存在，请重新打包"
          }
        }
        persistState()
      },
    })

    sseConnections.set(sessionId, sse)
    sse.connect(sessionId)
  }

  function disconnectSSE(sessionId: string): void {
    const sse = sseConnections.get(sessionId)
    if (sse) {
      sse.disconnect()
      sseConnections.delete(sessionId)
    }
  }

  function createTaskProgress(
    taskId: string,
    sessionId: string,
    author: string,
    name: string,
    version: string,
    architecture: Architecture = "linux-amd64",
  ): PackTaskProgress {
    return {
      taskId,
      sessionId,
      author,
      name,
      version,
      architecture,
      status: "pending",
      currentStep: null,
      stepMessage: null,
      stepDetail: null,
      progress: null,
      errorMessage: null,
      rawError: null,
      logs: [],
      downloaded: false,
    }
  }

  async function submitPack(plugins: PackPluginItem[]): Promise<PackResponse> {
    const response = await startPack({ plugins })

    sessions.value.set(response.session_id, {
      sessionId: response.session_id,
      taskIds: response.tasks.map((t) => t.task_id),
      completed: false,
    })

    for (const task of response.tasks) {
      tasks.value.set(task.task_id, createTaskProgress(
        task.task_id,
        response.session_id,
        task.author,
        task.name,
        task.version,
      ))
    }

    persistState()
    connectSSE(response.session_id)
    connectionError.value = null

    return response
  }

  async function startPackFromCart(items: Plugin[]): Promise<void> {
    const plugins: PackPluginItem[] = items.map((item) => ({
      author: item.org,
      name: item.name,
      version: item.latest_version,
      source: "marketplace" as const,
      architecture: selectedArchitecture.value,
    }))
    await submitPack(plugins)
  }

  async function appendPack(items: Plugin[]): Promise<void> {
    const plugins: PackPluginItem[] = items.map((item) => ({
      author: item.org,
      name: item.name,
      version: item.latest_version,
      source: "marketplace" as const,
      architecture: selectedArchitecture.value,
    }))
    await submitPack(plugins)
  }

  function enqueuePlugin(plugin: Plugin): void {
    if (queuedItems.value.some((item) => item.plugin_id === plugin.plugin_id)) return
    queuedItems.value.push(plugin)
    saveQueueToStorage(queuedItems.value)
  }

  function removeFromQueue(pluginId: string): void {
    const index = queuedItems.value.findIndex((item) => item.plugin_id === pluginId)
    if (index === -1) return
    queuedItems.value.splice(index, 1)
    saveQueueToStorage(queuedItems.value)
  }

  function clearQueue(): void {
    queuedItems.value = []
    saveQueueToStorage(queuedItems.value)
  }

  function isInQueue(pluginId: string): boolean {
    return queuedItems.value.some((item) => item.plugin_id === pluginId)
  }

  async function dequeueAndPack(architecture: Architecture): Promise<void> {
    if (queuedItems.value.length === 0) return
    const plugins: PackPluginItem[] = queuedItems.value.map((item) => ({
      author: item.org,
      name: item.name,
      version: item.latest_version,
      source: "marketplace" as const,
      architecture,
    }))
    queuedItems.value = []
    saveQueueToStorage(queuedItems.value)
    await submitPack(plugins)
  }

  async function startPackFromQueue(architecture: Architecture): Promise<void> {
    await dequeueAndPack(architecture)
  }

  async function cancelPack(): Promise<void> {
    const activeSessions: string[] = []
    for (const session of sessions.value.values()) {
      if (!session.completed) {
        activeSessions.push(session.sessionId)
      }
    }

    for (const sid of activeSessions) {
      disconnectSSE(sid)
    }

    try {
      await Promise.all(activeSessions.map((sid) => cancelSession(sid)))
    } catch {
      // ignore cancel API errors
    }

    for (const task of tasks.value.values()) {
      if (task.status === "pending" || task.status === "running") {
        task.status = "cancelled"
      }
    }

    for (const sid of activeSessions) {
      const session = sessions.value.get(sid)
      if (session) {
        session.completed = true
      }
    }

    persistState()
  }

  function retryFailed(taskId: string): void {
    const task = tasks.value.get(taskId)
    if (!task || (task.status !== "failed" && task.status !== "cancelled")) return

    const plugin: PackPluginItem = {
      author: task.author,
      name: task.name,
      version: task.version,
      source: "marketplace",
      architecture: task.architecture,
    }

    tasks.value.delete(taskId)
    const session = sessions.value.get(task.sessionId)
    if (session) {
      session.taskIds = session.taskIds.filter((id) => id !== taskId)
    }
    persistState()

    submitPack([plugin])
  }

  function downloadResult(taskId: string): void {
    const task = tasks.value.get(taskId)
    if (!task || task.status !== "success") return

    const url = getDownloadUrl(taskId)
    const link = document.createElement("a")
    link.href = url
    link.download = ""
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    task.downloaded = true
    persistState()
  }

  function clearConnectionError(): void {
    connectionError.value = null
  }

  function restoreSessions(): void {
    for (const session of sessions.value.values()) {
      if (!session.completed) {
        connectSSE(session.sessionId)
      }
    }
  }

  function clearCompleted(): void {
    for (const [id, session] of sessions.value.entries()) {
      if (session.completed) {
        for (const taskId of session.taskIds) {
          tasks.value.delete(taskId)
        }
        sessions.value.delete(id)
      }
    }
    persistState()
  }

  function setArchitecture(architecture: Architecture): void {
    selectedArchitecture.value = architecture
    localStorage.setItem("selected-architecture", architecture)
  }

  function loadSavedArchitecture(): void {
    const saved = localStorage.getItem("selected-architecture")
    if (!saved) return
    const validValues = ARCHITECTURE_OPTIONS.map((o) => o.value)
    if (validValues.includes(saved as Architecture)) {
      selectedArchitecture.value = saved as Architecture
    }
  }

  async function uploadLocalFiles(files: File[]): Promise<BatchUploadResponse> {
    isUploading.value = true
    uploadErrors.value = []
    try {
      const response = await uploadPlugins(files)
      uploadedPlugins.value.push(...response.success)
      uploadErrors.value = response.failed
      return response
    } catch (err) {
      const apiError = err as { message?: string }
      uploadErrors.value = files.map((f) => ({
        filename: f.name,
        error: apiError.message || "上传失败",
      }))
      return { success: [], failed: uploadErrors.value }
    } finally {
      isUploading.value = false
    }
  }

  function removeUploadedPlugin(uploadId: string): void {
    const index = uploadedPlugins.value.findIndex((p) => p.upload_id === uploadId)
    if (index !== -1) {
      uploadedPlugins.value.splice(index, 1)
    }
  }

  function clearUploadErrors(): void {
    uploadErrors.value = []
  }

  function isUploadedPluginInQueue(uploadId: string): boolean {
    const plugin = uploadedPlugins.value.find((p) => p.upload_id === uploadId)
    if (!plugin) return false
    return queuedItems.value.some(
      (item) => item.org === plugin.author && item.name === plugin.name,
    )
  }

  async function enqueueUploadedPlugin(plugin: UploadResponse): Promise<void> {
    const fakePlugin: Plugin = {
      type: "tool",
      plugin_id: `${plugin.author}/${plugin.name}`,
      name: plugin.name,
      org: plugin.author,
      latest_version: plugin.version,
      label: plugin.label,
      brief: plugin.label,
      introduction: "",
      readme_meta: { available_languages: [] },
      category: "",
      install_count: 0,
      created_at: "",
      updated_at: "",
      latest_package_identifier: "",
      status: "active",
      tags: [],
      verification: null,
      badges: [],
      repository: null,
      resource: null,
      privacy_policy: "",
    }

    if (queuedItems.value.some((item) => item.plugin_id === fakePlugin.plugin_id)) return
    queuedItems.value.push(fakePlugin)
    saveQueueToStorage(queuedItems.value)
  }

  async function packUploadedPlugin(plugin: UploadResponse, architecture: Architecture): Promise<void> {
    const packItem: PackPluginItem = {
      author: plugin.author,
      name: plugin.name,
      version: plugin.version,
      source: "local",
      upload_id: plugin.upload_id,
      architecture,
    }
    await submitPack([packItem])
  }

  return {
    sessions,
    tasks,
    isPacking,
    taskList,
    hasTasks,
    connectionError,
    selectedArchitecture,
    queuedItems,
    setArchitecture,
    loadSavedArchitecture,
    startPackFromCart,
    startPackFromQueue,
    enqueuePlugin,
    dequeueAndPack,
    removeFromQueue,
    clearQueue,
    isInQueue,
    appendPack,
    cancelPack,
    retryFailed,
    downloadResult,
    clearConnectionError,
    restoreSessions,
    clearCompleted,
    handleSSEEvent,
    uploadedPlugins,
    uploadErrors,
    isUploading,
    uploadLocalFiles,
    removeUploadedPlugin,
    clearUploadErrors,
    isUploadedPluginInQueue,
    enqueueUploadedPlugin,
    packUploadedPlugin,
  }
})
