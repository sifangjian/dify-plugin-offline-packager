import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

let mockInstance: {
  addEventListener: ReturnType<typeof vi.fn>
  close: ReturnType<typeof vi.fn>
  onopen: ((this: EventSource, ev: Event) => void) | null
  onerror: ((this: EventSource, ev: Event) => void) | null
  simulateOpen: () => void
  simulateError: () => void
  simulateEvent: (type: string, data: unknown) => void
} | null = null

let eventSourceCalls: string[] = []

class MockEventSource {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 2

  CONNECTING = 0
  OPEN = 1
  CLOSED = 2
  readyState = 0
  url = ""
  withCredentials = false

  private _onopen: ((this: EventSource, ev: Event) => void) | null = null
  private _onerror: ((this: EventSource, ev: Event) => void) | null = null
  private _onmessage: ((this: EventSource, ev: MessageEvent) => void) | null = null
  private listeners: Record<string, Array<(event: MessageEvent) => void>> = {}

  addEventListener = vi.fn((type: string, handler: (event: MessageEvent) => void) => {
    if (!this.listeners[type]) this.listeners[type] = []
    this.listeners[type].push(handler)
  })

  removeEventListener = vi.fn()
  dispatchEvent = vi.fn()

  close = vi.fn(() => {
    this._onopen = null
    this._onerror = null
  })

  get onopen() { return this._onopen }
  set onopen(fn: ((this: EventSource, ev: Event) => void) | null) { this._onopen = fn }

  get onerror() { return this._onerror }
  set onerror(fn: ((this: EventSource, ev: Event) => void) | null) { this._onerror = fn }

  get onmessage() { return this._onmessage }
  set onmessage(fn: ((this: EventSource, ev: MessageEvent) => void) | null) { this._onmessage = fn }

  simulateOpen = () => {
    if (this._onopen) this._onopen.call({} as EventSource, new Event("open"))
  }

  simulateError = () => {
    if (this._onerror) this._onerror.call({} as EventSource, new Event("error"))
  }

  simulateEvent = (type: string, data: unknown) => {
    const handlers = this.listeners[type] || []
    for (const handler of handlers) {
      handler({ data: JSON.stringify(data) } as MessageEvent)
    }
  }

  constructor(url: string) {
    eventSourceCalls.push(url)
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    mockInstance = this
  }
}

describe("useSSE", () => {
  let originalEventSource: typeof globalThis.EventSource

  beforeEach(() => {
    vi.useFakeTimers()
    originalEventSource = globalThis.EventSource
    globalThis.EventSource = MockEventSource as unknown as typeof EventSource
    mockInstance = null
    eventSourceCalls = []
  })

  afterEach(() => {
    vi.useRealTimers()
    globalThis.EventSource = originalEventSource
    mockInstance = null
  })

  describe("connect", () => {
    it("should create EventSource connecting to /sse/pack/{sessionId}", async () => {
      const onEvent = vi.fn()
      const { useSSE: useSSEFresh } = await import("@/composables/useSSE")
      const { connect } = useSSEFresh({ onEvent })

      connect("session-123")

      expect(eventSourceCalls).toContain("/sse/pack/session-123")
    })

    it("should set isConnected to true when connection opens", async () => {
      const onEvent = vi.fn()
      const { useSSE: useSSEFresh } = await import("@/composables/useSSE")
      const { connect, isConnected } = useSSEFresh({ onEvent })

      connect("session-123")
      expect(isConnected.value).toBe(false)

      mockInstance!.simulateOpen()
      expect(isConnected.value).toBe(true)
    })
  })

  describe("event handling", () => {
    it("should call onEvent with parsed SSEEvent when receiving step_progress", async () => {
      const onEvent = vi.fn()
      const { useSSE: useSSEFresh } = await import("@/composables/useSSE")
      const { connect } = useSSEFresh({ onEvent })

      connect("session-123")
      mockInstance!.simulateOpen()

      const eventData = {
        event_type: "step_progress",
        session_id: "session-123",
        timestamp: "2024-01-01T00:00:00Z",
        task_id: "task-1",
        plugin_name: "google",
        step: "resolving_deps",
        message: "正在解析依赖...",
      }
      mockInstance!.simulateEvent("step_progress", eventData)

      expect(onEvent).toHaveBeenCalledWith(eventData)
    })

    it("should call onEvent for all 6 event types", async () => {
      const onEvent = vi.fn()
      const { useSSE: useSSEFresh } = await import("@/composables/useSSE")
      const { connect } = useSSEFresh({ onEvent })

      connect("session-123")
      mockInstance!.simulateOpen()

      const eventTypes = [
        "session_started",
        "task_started",
        "step_progress",
        "task_success",
        "task_failed",
        "session_completed",
      ]

      for (const type of eventTypes) {
        const data = {
          event_type: type,
          session_id: "session-123",
          timestamp: "2024-01-01T00:00:00Z",
        }
        mockInstance!.simulateEvent(type, data)
      }

      expect(onEvent).toHaveBeenCalledTimes(6)
    })

    it("should silently ignore events with invalid JSON", async () => {
      const onEvent = vi.fn()
      const { useSSE: useSSEFresh } = await import("@/composables/useSSE")
      const { connect } = useSSEFresh({ onEvent })

      connect("session-123")
      mockInstance!.simulateOpen()

      const addEventListenerCalls = mockInstance!.addEventListener.mock.calls
      const stepProgressHandlers = addEventListenerCalls
        .filter((call: unknown[]) => call[0] === "step_progress")
        .map((call: unknown[]) => call[1])

      for (const handler of stepProgressHandlers) {
        (handler as (e: MessageEvent) => void)({ data: "not-valid-json{{{" } as MessageEvent)
      }

      expect(onEvent).not.toHaveBeenCalled()
    })
  })

  describe("disconnect", () => {
    it("should close EventSource and set isConnected to false", async () => {
      const onEvent = vi.fn()
      const { useSSE: useSSEFresh } = await import("@/composables/useSSE")
      const { connect, disconnect, isConnected } = useSSEFresh({ onEvent })

      connect("session-123")
      mockInstance!.simulateOpen()
      expect(isConnected.value).toBe(true)

      disconnect()
      expect(mockInstance!.close).toHaveBeenCalled()
      expect(isConnected.value).toBe(false)
    })

    it("should stop retry after disconnect", async () => {
      const onEvent = vi.fn()
      const { useSSE: useSSEFresh } = await import("@/composables/useSSE")
      const { connect, disconnect } = useSSEFresh({ onEvent })

      connect("session-123")
      mockInstance!.simulateOpen()
      disconnect()

      vi.advanceTimersByTime(30000)

      expect(eventSourceCalls).toHaveLength(1)
    })
  })

  describe("auto-reconnect", () => {
    it("should attempt reconnect with increasing delay on error", async () => {
      const onEvent = vi.fn()
      const { useSSE: useSSEFresh } = await import("@/composables/useSSE")
      const { connect, isConnected } = useSSEFresh({ onEvent })

      connect("session-123")
      mockInstance!.simulateOpen()
      expect(isConnected.value).toBe(true)

      mockInstance!.simulateError()
      expect(isConnected.value).toBe(false)

      vi.advanceTimersByTime(3000)
      expect(eventSourceCalls).toHaveLength(2)

      mockInstance!.simulateError()
      vi.advanceTimersByTime(6000)
      expect(eventSourceCalls).toHaveLength(3)

      mockInstance!.simulateError()
      vi.advanceTimersByTime(9000)
      expect(eventSourceCalls).toHaveLength(4)
    })

    it("should call onError after max retries exceeded", async () => {
      const onEvent = vi.fn()
      const onError = vi.fn()
      const { useSSE: useSSEFresh } = await import("@/composables/useSSE")
      const { connect } = useSSEFresh({ onEvent, onError, reconnectAttempts: 3 })

      connect("session-123")
      mockInstance!.simulateOpen()

      for (let i = 0; i < 3; i++) {
        mockInstance!.simulateError()
        vi.advanceTimersByTime(3000 * (i + 1))
      }

      mockInstance!.simulateError()

      expect(onError).toHaveBeenCalled()
    })

    it("should reset retry count on successful reconnection", async () => {
      const onEvent = vi.fn()
      const onError = vi.fn()
      const { useSSE: useSSEFresh } = await import("@/composables/useSSE")
      const { connect } = useSSEFresh({ onEvent, onError, reconnectAttempts: 2 })

      connect("session-123")
      mockInstance!.simulateOpen()

      mockInstance!.simulateError()
      vi.advanceTimersByTime(3000)
      expect(eventSourceCalls).toHaveLength(2)

      mockInstance!.simulateOpen()

      mockInstance!.simulateError()
      vi.advanceTimersByTime(3000)
      expect(eventSourceCalls).toHaveLength(3)

      mockInstance!.simulateError()
      vi.advanceTimersByTime(6000)
      expect(eventSourceCalls).toHaveLength(4)

      mockInstance!.simulateError()
      expect(onError).toHaveBeenCalled()
    })

    it("should call onNotFound when connection never succeeded after retries", async () => {
      const onEvent = vi.fn()
      const onError = vi.fn()
      const onNotFound = vi.fn()
      const { useSSE: useSSEFresh } = await import("@/composables/useSSE")
      const { connect } = useSSEFresh({ onEvent, onError, onNotFound, reconnectAttempts: 2 })

      connect("session-123")

      for (let i = 0; i < 2; i++) {
        mockInstance!.simulateError()
        vi.advanceTimersByTime(3000 * (i + 1))
      }

      mockInstance!.simulateError()

      expect(onNotFound).toHaveBeenCalled()
      expect(onError).not.toHaveBeenCalled()
    })
  })
})
