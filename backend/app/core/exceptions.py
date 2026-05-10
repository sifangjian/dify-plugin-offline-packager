from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code


class MarketplaceAPIError(AppException):
    def __init__(
        self,
        message: str = "无法连接到 Marketplace API，请稍后重试",
        code: str = "MARKETPLACE_API_ERROR",
        status_code: int = 503,
    ):
        super().__init__(message=message, code=code, status_code=status_code)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "服务内部错误，请稍后重试"}},
    )
