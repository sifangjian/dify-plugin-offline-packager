import { describe, it, expect, vi, beforeEach } from "vitest"
import type { SearchParams, BatchParams } from "@/types/marketplace"

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock("@/api/client", () => ({
  default: {
    get: mockGet,
    post: mockPost,
  },
}))

describe("Marketplace API", () => {
  beforeEach(() => {
    vi.resetModules()
    mockGet.mockReset()
    mockPost.mockReset()
  })

  describe("searchPlugins", () => {
    it("should send POST request to /v1/marketplace/search", async () => {
      mockPost.mockResolvedValue({ data: { plugins: [], total: 0 } })
      const { searchPlugins } = await import("@/api/marketplace")

      const params: SearchParams = {
        keyword: "test",
        category: "tool",
        page: 1,
        page_size: 20,
      }
      await searchPlugins(params)

      expect(mockPost).toHaveBeenCalledWith(
        "/v1/marketplace/search",
        params,
        { signal: undefined }
      )
    })
  })

  describe("getPluginDetail", () => {
    it("should send GET request to /v1/marketplace/{author}/{name}", async () => {
      mockGet.mockResolvedValue({ data: {} })
      const { getPluginDetail } = await import("@/api/marketplace")

      await getPluginDetail("langgenius", "google")

      expect(mockGet).toHaveBeenCalledWith(
        "/v1/marketplace/langgenius/google",
        { params: {} }
      )
    })

    it("should send GET request with language param when provided", async () => {
      mockGet.mockResolvedValue({ data: {} })
      const { getPluginDetail } = await import("@/api/marketplace")

      await getPluginDetail("langgenius", "google", "zh_Hans")

      expect(mockGet).toHaveBeenCalledWith(
        "/v1/marketplace/langgenius/google",
        { params: { language: "zh_Hans" } }
      )
    })
  })

  describe("getCollections", () => {
    it("should send GET request with page and page_size params", async () => {
      mockGet.mockResolvedValue({ data: { collections: [], total: 0 } })
      const { getCollections } = await import("@/api/marketplace")

      await getCollections(1, 20)

      expect(mockGet).toHaveBeenCalledWith(
        "/v1/marketplace/collections",
        { params: { page: 1, page_size: 20 } }
      )
    })

    it("should use default values when no params provided", async () => {
      mockGet.mockResolvedValue({ data: { collections: [], total: 0 } })
      const { getCollections } = await import("@/api/marketplace")

      await getCollections()

      expect(mockGet).toHaveBeenCalledWith(
        "/v1/marketplace/collections",
        { params: { page: 1, page_size: 20 } }
      )
    })
  })

  describe("batchGetPlugins", () => {
    it("should send POST request to /v1/marketplace/batch", async () => {
      mockPost.mockResolvedValue({ data: { plugins: [] } })
      const { batchGetPlugins } = await import("@/api/marketplace")

      const params: BatchParams = { plugin_ids: ["id1", "id2"] }
      await batchGetPlugins(params)

      expect(mockPost).toHaveBeenCalledWith(
        "/v1/marketplace/batch",
        params
      )
    })
  })
})
