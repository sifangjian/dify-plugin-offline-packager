import apiClient from "./client"
import type {
  SearchParams,
  SearchResult,
  Plugin,
  CollectionsResult,
  BatchParams,
  BatchResult,
} from "@/types/marketplace"

export async function searchPlugins(params: SearchParams, signal?: AbortSignal): Promise<SearchResult> {
  const response = await apiClient.post<SearchResult>(
    "/v1/marketplace/search",
    params,
    { signal }
  )
  return response.data
}

export async function getPluginDetail(author: string, name: string): Promise<Plugin> {
  const response = await apiClient.get<Plugin>(
    `/v1/marketplace/${author}/${name}`
  )
  return response.data
}

export async function getCollections(
  page: number = 1,
  pageSize: number = 20
): Promise<CollectionsResult> {
  const response = await apiClient.get<CollectionsResult>(
    "/v1/marketplace/collections",
    { params: { page, page_size: pageSize } }
  )
  return response.data
}

export async function batchGetPlugins(params: BatchParams): Promise<BatchResult> {
  const response = await apiClient.post<BatchResult>(
    "/v1/marketplace/batch",
    params
  )
  return response.data
}
