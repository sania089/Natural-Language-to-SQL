"""Typed domain errors. Each carries an HTTP status and a stable machine-readable code."""


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, *, extra: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.extra = extra or {}


class InvalidQuestionError(AppError):
    status_code = 422
    code = "INVALID_QUESTION"


class CannotAnswerError(AppError):
    status_code = 422
    code = "CANNOT_ANSWER"


class SqlRejectedError(AppError):
    status_code = 422
    code = "SQL_REJECTED"


class QueryFailedError(AppError):
    status_code = 422
    code = "QUERY_FAILED"


class QueryTimeoutError(AppError):
    status_code = 504
    code = "QUERY_TIMEOUT"


class LlmError(AppError):
    status_code = 502
    code = "LLM_UNAVAILABLE"


class LlmRateLimitError(LlmError):
    status_code = 429
    code = "LLM_RATE_LIMITED"


class LlmTimeoutError(LlmError):
    status_code = 504
    code = "LLM_TIMEOUT"
