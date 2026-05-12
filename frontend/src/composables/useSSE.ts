import { ref, onUnmounted } from "vue"
import type { SSEEvent } from "@/types/packager"
import type { Ref } from "vue"

interface UseSSEOptions {
  onEvent: (event: SSEEvent) => void
  onError?: (error: Event) => void
  reconnectAttempts?: number
  reconnectInterval?: number
}

interface UseSSEReturn {
  connect: (sessionId: string) => void
  disconnect: () => void
  isConnected: Ref<boolean>
}

const SSE_BASE_URL = import.meta.env.VITE_SSE_BASE_URL || "/sse"

export function useSSE(options: UseSSEOptions): UseSSEReturn {
  const isConnected = ref(false)
  let eventSource: EventSource | null = null
  let currentSessionId: string | null = null
  let retryCount = 0
  const maxRetries = options.reconnectAttempts ?? 3
  const retryDelay = options.reconnectInterval ?? 3000
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function connect(sessionId: string): void {
    disconnect()
    currentSessionId = sessionId
    retryCount = 0
    createEventSource(sessionId)
  }

  function createEventSource(sessionId: string): void {
    const url = `${SSE_BASE_URL}/pack/${sessionId}`
    eventSource = new EventSource(url)

    eventSource.onopen = () => {
      isConnected.value = true
      retryCount = 0
    }

    const eventTypes = [
      "session_started",
      "task_started",
      "step_progress",
      "task_success",
      "task_failed",
      "session_completed",
    ]

    for (const type of eventTypes) {
      eventSource.addEventListener(type, (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as SSEEvent
          options.onEvent(data)
        } catch {
          // ignore parse failures
        }
      })
    }

    eventSource.onerror = () => {
      isConnected.value = false
      eventSource?.close()
      eventSource = null

      if (retryCount < maxRetries) {
        retryCount++
        reconnectTimer = setTimeout(() => {
          if (currentSessionId) {
            createEventSource(currentSessionId)
          }
        }, retryDelay * retryCount)
      } else {
        options.onError?.(new Event("SSE connection failed"))
      }
    }
  }

  function disconnect(): void {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    isConnected.value = false
    currentSessionId = null
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    connect,
    disconnect,
    isConnected,
  }
}
