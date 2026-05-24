import apiClient from "./client"
import type { PackRequest, PackResponse } from "@/types/packager"
import type { BatchUploadResponse } from "@/types/upload"

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

export async function uploadPlugins(files: File[]): Promise<BatchUploadResponse> {
  const formData = new FormData()
  files.forEach((file) => {
    formData.append("files", file)
  })

  const response = await apiClient.post<BatchUploadResponse>(
    "/v1/plugins/upload",
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      timeout: 300000,
    }
  )
  return response.data
}
