export type PackStep = "downloading" | "resolving_deps" | "downloading_deps" | "packaging"

export type TaskStatus = "pending" | "running" | "success" | "failed" | "cancelled"

export type SSEEventType =
  | "session_started"
  | "task_started"
  | "step_progress"
  | "task_success"
  | "task_failed"
  | "session_completed"

export interface PackPluginItem {
  author: string
  name: string
  version: string
  source: "marketplace" | "local"
}

export interface PackRequest {
  plugins: PackPluginItem[]
}

export interface PackTaskSummary {
  task_id: string
  author: string
  name: string
  version: string
  status: TaskStatus
}

export interface PackResponse {
  session_id: string
  tasks: PackTaskSummary[]
}

export interface SSEEventBase {
  event_type: SSEEventType
  session_id: string
  timestamp: string
}

export interface SessionStartedEvent extends SSEEventBase {
  event_type: "session_started"
  total: number
}

export interface TaskStartedEvent extends SSEEventBase {
  event_type: "task_started"
  task_id: string
  plugin_name: string
  plugin_version: string
}

export interface StepProgressEvent extends SSEEventBase {
  event_type: "step_progress"
  task_id: string
  plugin_name: string
  step: PackStep
  message: string
  detail?: string
  progress?: { current: number; total: number }
}

export interface TaskSuccessEvent extends SSEEventBase {
  event_type: "task_success"
  task_id: string
  plugin_name: string
  plugin_version: string
}

export interface TaskFailedEvent extends SSEEventBase {
  event_type: "task_failed"
  task_id: string
  plugin_name: string
  step: PackStep
  message: string
  raw_error: string
}

export interface SessionCompletedEvent extends SSEEventBase {
  event_type: "session_completed"
  success_count: number
  failed_count: number
}

export type SSEEvent =
  | SessionStartedEvent
  | TaskStartedEvent
  | StepProgressEvent
  | TaskSuccessEvent
  | TaskFailedEvent
  | SessionCompletedEvent

export interface PackTaskProgress {
  taskId: string
  sessionId: string
  author: string
  name: string
  version: string
  status: TaskStatus
  currentStep: PackStep | null
  stepMessage: string | null
  stepDetail: string | null
  progress: { current: number; total: number } | null
  errorMessage: string | null
  rawError: string | null
  logs: StepLog[]
  downloaded: boolean
}

export interface StepLog {
  step: PackStep
  message: string
  timestamp: string
  isError?: boolean
}

export const STEP_LABELS: Record<PackStep, string> = {
  downloading: "正在下载插件包...",
  resolving_deps: "正在解析依赖...",
  downloading_deps: "正在下载依赖包...",
  packaging: "正在打包离线插件...",
}

export const STEP_ORDER: PackStep[] = [
  "downloading",
  "resolving_deps",
  "downloading_deps",
  "packaging",
]
