"""애플리케이션 커스텀 예외."""


class PromptChatException(Exception):
    """기본 애플리케이션 예외."""

    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR"):
        """
        Args:
            message: 에러 메시지
            error_code: 에러 코드 (기본값: INTERNAL_ERROR)
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class DatabaseException(PromptChatException):
    """데이터베이스 관련 예외."""

    def __init__(self, message: str, error_code: str = "DATABASE_ERROR"):
        super().__init__(message, error_code)


class ValidationException(PromptChatException):
    """검증 실패 예외."""

    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        super().__init__(message, error_code)
