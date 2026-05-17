"""
异常处理模块

定义应用自定义异常类和全局异常处理器。

异常层次：
- AppException: 应用基础异常
  - MarketplaceAPIError: Marketplace API 相关异常
  - PackageError: 打包相关异常
  - StorageError: 存储相关异常

异常处理器：
- app_exception_handler: 处理 AppException 及其子类
- unhandled_exception_handler: 处理未捕获的异常
"""

from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """
    应用基础异常

    所有自定义异常的基类，提供统一的错误响应格式。

    Attributes:
        message: 错误消息
        code: 错误代码
        status_code: HTTP 状态码
    """

    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code


class MarketplaceAPIError(AppException):
    """
    Marketplace API 异常

    当与 Dify Marketplace 交互失败时抛出。

    默认状态码为 503 (Service Unavailable)。
    """

    def __init__(
        self,
        message: str = "无法连接到 Marketplace API，请稍后重试",
        code: str = "MARKETPLACE_API_ERROR",
        status_code: int = 503,
    ):
        super().__init__(message=message, code=code, status_code=status_code)


class PackageError(AppException):
    """
    打包异常

    当打包过程中出现错误时抛出。

    默认状态码为 500 (Internal Server Error)。
    """

    def __init__(
        self,
        message: str = "打包过程失败",
        code: str = "PACKAGE_ERROR",
        status_code: int = 500,
    ):
        super().__init__(message=message, code=code, status_code=status_code)


class StorageError(AppException):
    """
    存储异常

    当文件系统操作失败时抛出。

    默认状态码为 500 (Internal Server Error)。
    """

    def __init__(
        self,
        message: str = "文件存储操作失败",
        code: str = "STORAGE_ERROR",
        status_code: int = 500,
    ):
        super().__init__(message=message, code=code, status_code=status_code)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    应用异常处理器

    处理 AppException 及其子类异常，返回统一格式的错误响应。

    Args:
        request: FastAPI 请求对象
        exc: 异常实例

    Returns:
        JSONResponse: 包含错误信息的 JSON 响应
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    未处理异常处理器

    捕获所有未处理的异常，返回通用错误响应。
    避免向客户端暴露内部错误详情。

    Args:
        request: FastAPI 请求对象
        exc: 异常实例

    Returns:
        JSONResponse: 通用错误响应
    """
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "服务内部错误，请稍后重试"}},
    )
