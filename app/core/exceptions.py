from typing import Any

from fastapi import status


class CodeCompanionException(Exception):
    """Base exception for Code Companion."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ResourceNotFoundError(CodeCompanionException):
    def __init__(self, resource: str = "Resource", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=f"{resource} not found",
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ValidationError(CodeCompanionException):
    def __init__(self, message: str = "Validation failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class AuthenticationError(CodeCompanionException):
    def __init__(self, message: str = "Authentication failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            error_code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class LLMError(CodeCompanionException):
    def __init__(self, message: str = "LLM operation failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            error_code="LLM_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


def create_error_response(exc: CodeCompanionException) -> dict[str, Any]:
    return {
        "error": {
            "code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        }
    }
