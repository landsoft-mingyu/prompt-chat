from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    service: str


class DBHealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    db: int
