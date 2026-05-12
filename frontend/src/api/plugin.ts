import apiClient from "./client"
import type { PackRequest, PackResponse } from "@/types/packager"

export async function startPack(request: PackRequest): Promise<PackResponse> {
  const response = await apiClient.post<PackResponse>(
    "/v1/plugins/pack",
    request
  )
  return response.data
}

export async function cancelSession(sessionId: string): Promise<void> {
  await apiClient.post(`/v1/plugins/cancel/${sessionId}`)
}

export function getDownloadUrl(taskId: string): string {
  const baseURL = apiClient.defaults.baseURL || "/api"
  return `${baseURL}/v1/plugins/download/${taskId}`
}
