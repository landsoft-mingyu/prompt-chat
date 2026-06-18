"""Tests for Settings configuration."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


class TestSettings:
    """Settings 통합 테스트."""

    def test_settings_requires_cubrid_password(self):
        """CUBRID 비밀번호는 필수."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                cubrid_db="test_db",
                cubrid_user="test_user",
                llm_api_key="test-key",
            )
        # cubrid_password가 필수
        assert "cubrid_password" in str(exc_info.value)

    def test_settings_database_url_generation(self):
        """database_url property 테스트."""
        settings = Settings(
            cubrid_host="localhost",
            cubrid_port=33000,
            cubrid_db="royal",
            cubrid_user="royal",
            cubrid_password="test-pass",
            royal_password="royal-test-pass",
            royal_api_base_url="http://localhost:8080/api",
            llm_api_key="test-key",
        )
        assert settings.database_url == (
            "cubrid+pycubrid://royal:test-pass@localhost:33000/royal"
        )

    def test_settings_cors_defaults(self):
        """CORS 기본값 확인."""
        settings = Settings(
            cubrid_db="royal",
            cubrid_user="royal",
            cubrid_password="test-pass",
            royal_password="royal-test-pass",
            royal_api_base_url="http://localhost:8080/api",
            llm_api_key="test-key",
        )
        assert settings.cors_allow_origins == ["http://localhost:3000"]
