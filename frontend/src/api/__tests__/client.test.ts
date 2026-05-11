import type { AxiosError, InternalAxiosRequestConfig } from "axios"
import { describe, it, expect, vi, beforeEach } from "vitest"

vi.mock("@/types/marketplace", () => ({}))

describe("apiClient", () => {
  let apiClient: typeof import("@/api/client").default

  beforeEach(async () => {
    vi.resetModules()
    apiClient = (await import("@/api/client")).default
  })

  describe("instance configuration", () => {
    it("should use VITE_API_BASE_URL as baseURL", () => {
      expect(apiClient.defaults.baseURL).toBe("/api")
    })

    it("should set timeout to 10000ms", () => {
      expect(apiClient.defaults.timeout).toBe(10000)
    })
  })

  describe("response error interceptor", () => {
    it("should extract error message from backend error response (404)", async () => {
      const error: Partial<AxiosError> = {
        response: {
          data: { error: { code: "NOT_FOUND", message: "未找到该插件" } },
          status: 404,
          statusText: "Not Found",
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        },
        isAxiosError: true,
        name: "AxiosError",
        message: "Request failed with status code 404",
      }

      const interceptor = apiClient.interceptors.response.handlers![0]!
      const rejected = interceptor.rejected

      await expect(rejected!(error)).rejects.toEqual({
        status: 404,
        message: "未找到该插件",
      })
    })

    it("should return generic message for 500 without error field", async () => {
      const error: Partial<AxiosError> = {
        response: {
          data: {},
          status: 500,
          statusText: "Internal Server Error",
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        },
        isAxiosError: true,
        name: "AxiosError",
        message: "Request failed with status code 500",
      }

      const interceptor = apiClient.interceptors.response.handlers![0]!
      const rejected = interceptor.rejected

      await expect(rejected!(error)).rejects.toEqual({
        status: 500,
        message: "服务异常，请稍后重试",
      })
    })

    it("should return rate limit message for 429", async () => {
      const error: Partial<AxiosError> = {
        response: {
          data: {},
          status: 429,
          statusText: "Too Many Requests",
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        },
        isAxiosError: true,
        name: "AxiosError",
        message: "Request failed with status code 429",
      }

      const interceptor = apiClient.interceptors.response.handlers![0]!
      const rejected = interceptor.rejected

      await expect(rejected!(error)).rejects.toEqual({
        status: 429,
        message: "请求过于频繁，请稍后重试",
      })
    })

    it("should return timeout message for ECONNABORTED", async () => {
      const error: Partial<AxiosError> = {
        code: "ECONNABORTED",
        isAxiosError: true,
        name: "AxiosError",
        message: "timeout of 10000ms exceeded",
      }

      const interceptor = apiClient.interceptors.response.handlers![0]!
      const rejected = interceptor.rejected

      await expect(rejected!(error)).rejects.toEqual({
        status: 0,
        message: "网络请求超时",
      })
    })

    it("should return network error message when no response", async () => {
      const error: Partial<AxiosError> = {
        isAxiosError: true,
        name: "AxiosError",
        message: "Network Error",
      }

      const interceptor = apiClient.interceptors.response.handlers![0]!
      const rejected = interceptor.rejected

      await expect(rejected!(error)).rejects.toEqual({
        status: 0,
        message: "网络异常，请检查连接",
      })
    })

    it("should prefer backend error message over status-based defaults", async () => {
      const error: Partial<AxiosError> = {
        response: {
          data: { error: { code: "VALIDATION_ERROR", message: "参数校验失败" } },
          status: 400,
          statusText: "Bad Request",
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        },
        isAxiosError: true,
        name: "AxiosError",
        message: "Request failed with status code 400",
      }

      const interceptor = apiClient.interceptors.response.handlers![0]!
      const rejected = interceptor.rejected

      await expect(rejected!(error)).rejects.toEqual({
        status: 400,
        message: "参数校验失败",
      })
    })

    it("should return ApiError type with status and message for all error paths", async () => {
      const error: Partial<AxiosError> = {
        response: {
          data: {},
          status: 403,
          statusText: "Forbidden",
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        },
        isAxiosError: true,
        name: "AxiosError",
        message: "Request failed with status code 403",
      }

      const interceptor = apiClient.interceptors.response.handlers![0]!
      const rejected = interceptor.rejected

      try {
        await rejected!(error)
      } catch (apiError) {
        expect(apiError).toHaveProperty("status")
        expect(apiError).toHaveProperty("message")
        const err = apiError as { status: number; message: string }
        expect(typeof err.status).toBe("number")
        expect(typeof err.message).toBe("string")
      }
    })
  })
})
