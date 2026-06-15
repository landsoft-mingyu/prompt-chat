# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import create_engine

from app.api.routes import health
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_engine = create_engine(
        settings.DATABASE_URL, 
        pool_pre_ping=True,
    )
    yield
    app.state.db_engine.dispose()


app = FastAPI(
    title="Prompt Homepage API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)  