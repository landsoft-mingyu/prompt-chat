from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ──────────────────────────────────────────────
# FastAPI 전체 설정
# ──────────────────────────────────────────────


class Settings(BaseSettings):
    """애플리케이션 설정."""

    # Local Database
    cubrid_host: str = Field(default="localhost", description="CUBRID 호스트")
    cubrid_port: int = Field(default=33000, description="CUBRID 포트")
    cubrid_db: str = Field(description="CUBRID 데이터베이스")
    cubrid_user: str = Field(description="CUBRID 사용자")
    cubrid_password: str = Field(description="CUBRID 비밀번호")

    # ROYAL System Database (for reservation proxy)
    site_code: str = Field(default="ROYAL", description="사이트 코드")
    royal_host: str = Field(default="192.168.12.55", description="ROYAL 시스템 호스트")
    royal_port: int = Field(default=33000, description="ROYAL 시스템 포트")
    royal_db: str = Field(default="royal", description="ROYAL 데이터베이스")
    royal_user: str = Field(default="royal", description="ROYAL 사용자")
    royal_password: str = Field(description="ROYAL 비밀번호")

    # ROYAL System HTTP API
    royal_api_base_url: str = Field(description="ROYAL API 기본 URL")
    royal_api_timeout_sec: int = Field(
        default=30, description="ROYAL API 타임아웃 (초)"
    )
    royal_api_verify_ssl: bool | str = Field(
        default=False,
        description="ROYAL API SSL 검증. False=비활성, 또는 CA 번들 파일 경로 문자열",
    )

    # LLM
    llm_base_url: str = Field(
        default="http://192.168.12.57:18081/v1",
        description="LLM API 엔드포인트",
    )
    llm_model: str = Field(
        default="google/gemma-3-12b",
        description="사용할 LLM 모델명",
    )
    llm_api_key: str = Field(description="LLM API 인증 키")
    llm_timeout_sec: int = Field(default=30, description="LLM 요청 타임아웃 (초)")

    # CORS
    cors_allow_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="CORS 허용 origin 목록",
    )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def database_url(self) -> str:
        """로컬 데이터베이스 URL."""
        return (
            f"cubrid+pycubrid://{self.cubrid_user}:{self.cubrid_password}"
            f"@{self.cubrid_host}:{self.cubrid_port}/{self.cubrid_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """설정 객체를 캐시하여 반환 (request마다 재로드 방지)."""
    return Settings()
