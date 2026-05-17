import { defineStore } from "pinia"
import { ref, computed } from "vue"
import { useSSE } from "@/composables/useSSE"
import { startPack, cancelSession, getDownloadUrl } from "@/api/plugin"
import type {
  PackPluginItem,
  PackResponse,
  PackTaskProgress,
  SSEEvent,
} from "@/types/packager"
import type { Plugin } from "@/types/marketplace"

const PACKAGER_STORAGE_KEY = "dify-plugin-packager"

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

export const usePackagerStore = defineStore("packager", () => {
  const persisted = loadFromStorage()
  const sessions = ref(persisted.sessions)
  const tasks = ref(persisted.tasks)
  const connectionError = ref<string | null>(null)

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
  ): PackTaskProgress {
    return {
      taskId,
      sessionId,
      author,
      name,
      version,
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
    }))
    await submitPack(plugins)
  }

  async function appendPack(items: Plugin[]): Promise<void> {
    const plugins: PackPluginItem[] = items.map((item) => ({
      author: item.org,
      name: item.name,
      version: item.latest_version,
      source: "marketplace" as const,
    }))
    await submitPack(plugins)
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

  return {
    sessions,
    tasks,
    isPacking,
    taskList,
    hasTasks,
    connectionError,
    startPackFromCart,
    appendPack,
    cancelPack,
    retryFailed,
    downloadResult,
    clearConnectionError,
    restoreSessions,
    clearCompleted,
    handleSSEEvent,
  }
})
