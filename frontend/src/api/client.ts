import axios from "axios"
import type { ApiError } from "@/types/marketplace"

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 10000,
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const apiError: ApiError = {
      status: 0,
      message: "网络异常，请检查连接",
    }

    if (error.response) {
      apiError.status = error.response.status
      if (error.response.data?.error?.message) {
        apiError.message = error.response.data.error.message
      } else if (error.response.status === 429) {
        apiError.message = "请求过于频繁，请稍后重试"
      } else if (error.response.status >= 500) {
        apiError.message = "服务异常，请稍后重试"
      } else if (error.response.status === 404) {
        apiError.message = "未找到该资源"
      }
    } else if (error.code === "ECONNABORTED") {
      apiError.message = "网络请求超时"
    }

    return Promise.reject(apiError)
  }
)

export default apiClient
