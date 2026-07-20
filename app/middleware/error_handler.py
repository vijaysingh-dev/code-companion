from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.exceptions import CodeCompanionException, create_error_response


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CodeCompanionException)
    async def code_companion_exception_handler(request, exc: CodeCompanionException):
        return JSONResponse(
            status_code=exc.status_code,
            content=create_error_response(exc),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc: Exception):
        from app.core.exceptions import CodeCompanionException as CCException

        error = CCException(
            message="Internal server error",
            error_code="INTERNAL_ERROR",
        )
        return JSONResponse(
            status_code=error.status_code,
            content=create_error_response(error),
        )
