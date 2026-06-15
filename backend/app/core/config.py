from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    CUBRID_HOST: str
    CUBRID_PORT: int
    CUBRID_DB: str
    CUBRID_USER: str
    CUBRID_PASSWORD: str

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"cubrid+pycubrid://{self.CUBRID_USER}:{self.CUBRID_PASSWORD}"
            f"@{self.CUBRID_HOST}:{self.CUBRID_PORT}/{self.CUBRID_DB}"
        )


settings = Settings()
