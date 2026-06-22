from fastapi import Depends, Request
from sqlalchemy import Engine

from app.adapters.db.base import IDBClient
from app.adapters.db.cubrid import CubridClient
from app.adapters.http.royal_api import RoyalApi
from app.adapters.interfaces.reservation_api_client import IReservationApiClient
from app.adapters.llm.vllm_client import VLLMClient
from app.core.config import Settings, get_settings
from app.repositories.cubrid.reservation_repository import RoyalReservationRepository
from app.repositories.health_repository import HealthRepository
from app.repositories.interfaces.chat_orchestrator import IChatOrchestrator
from app.repositories.interfaces.embedding_client import IEmbeddingClient
from app.repositories.interfaces.health_repository import IHealthRepository
from app.repositories.interfaces.intent_router import IIntentRouter
from app.repositories.interfaces.llm_client import ILLMClient
from app.repositories.interfaces.rag_search_service import IRAGSearchService
from app.repositories.interfaces.reservation_form_service import IReservationFormService
from app.repositories.interfaces.reservation_orchestrator import (
    IReservationOrchestrator,
)
from app.repositories.interfaces.session_store import SessionStore
from app.repositories.interfaces.slot_filling_service import ISlotFillingService
from app.repositories.interfaces.vector_repository import VectorRepository
from app.repositories.milvus.vector_repository import MilvusVectorRepository
from app.services.chat.chat_orchestrator import ChatOrchestrator
from app.services.chat.intent_router import LLMIntentRouter
from app.services.chat.reservation_orchestrator import ReservationOrchestrator
from app.services.chat.slot_filling import SlotFillingService
from app.services.health_service import HealthService
from app.services.rag.embedding_client import EmbeddingClient
from app.services.rag.rag_search_service import RAGSearchService
from app.services.reservation.form_schema import ReservationFormService


def get_app_settings() -> Settings:
    """설정 객체 반환 (get_settings()는 내부에서 @lru_cache 처리)."""
    return get_settings()


def get_db_engine(request: Request) -> Engine:
    """request.app.state에서 DB engine 반환."""
    return request.app.state.db_engine


def get_db_client(engine: Engine = Depends(get_db_engine)) -> IDBClient:
    """CubridClient 인스턴스 생성."""
    return CubridClient(engine)


def get_health_repository(
    client: IDBClient = Depends(get_db_client),
) -> IHealthRepository:
    """HealthRepository 인스턴스 생성."""
    return HealthRepository(client)


def get_health_service(
    repository: IHealthRepository = Depends(get_health_repository),
) -> HealthService:
    """HealthService 인스턴스 생성."""
    return HealthService(repository)


def get_reservation_repository(
    settings: Settings = Depends(get_app_settings),
) -> RoyalReservationRepository:
    """RoyalReservationRepository 인스턴스 생성."""
    return RoyalReservationRepository(settings)


def get_royal_api(
    request: Request,
    settings: Settings = Depends(get_app_settings),
) -> IReservationApiClient:
    """RoyalApi 인스턴스 생성 (app.state의 싱글톤 httpx.AsyncClient 사용)."""
    client = request.app.state.royal_api_client
    return RoyalApi(client, settings)


def get_vector_repository(
    settings: Settings = Depends(get_app_settings),
) -> VectorRepository:
    """MilvusVectorRepository 인스턴스 생성."""
    return MilvusVectorRepository(uri=settings.milvus_uri)


def get_embedding_client(
    settings: Settings = Depends(get_app_settings),
) -> IEmbeddingClient:
    """EmbeddingClient 인스턴스 생성."""
    return EmbeddingClient(base_url=settings.embedding_url)


def get_rag_search_service(
    settings: Settings = Depends(get_app_settings),
    vector_repo: VectorRepository = Depends(get_vector_repository),
    embedding_client: EmbeddingClient = Depends(get_embedding_client),
) -> IRAGSearchService:
    """RAGSearchService 인스턴스 생성."""
    return RAGSearchService(
        vector_repo=vector_repo,
        embedding_client=embedding_client,
        collection_name=settings.milvus_collection,
    )


# ── Chat Orchestrator 관련 ─────────────────────────────────────


def get_redis_session_store(request: Request) -> SessionStore:
    """app.state의 싱글톤 RedisSessionStore 반환 (커넥션 풀 공유)."""
    return request.app.state.session_store


def get_llm_client(
    request: Request,
    settings: Settings = Depends(get_app_settings),
) -> ILLMClient:
    """VLLMClient 인스턴스 생성 (app.state의 싱글톤 httpx.AsyncClient 사용)."""
    client = request.app.state.llm_client
    return VLLMClient(
        client=client,
        model=settings.llm_model,
        timeout_sec=settings.llm_timeout_sec,
    )


def get_slot_filling_service(
    llm_client: ILLMClient = Depends(get_llm_client),
) -> ISlotFillingService:
    """SlotFillingService 인스턴스 생성."""
    return SlotFillingService(llm_client=llm_client)


def get_intent_router(
    llm_client: ILLMClient = Depends(get_llm_client),
) -> IIntentRouter:
    """LLMIntentRouter 인스턴스 생성."""
    return LLMIntentRouter(llm_client=llm_client)


def get_reservation_orchestrator(
    api_client: IReservationApiClient = Depends(get_royal_api),
    slot_service: ISlotFillingService = Depends(get_slot_filling_service),
    session_store: SessionStore = Depends(get_redis_session_store),
) -> IReservationOrchestrator:
    """ReservationOrchestrator 인스턴스 생성."""
    return ReservationOrchestrator(
        api_client=api_client,
        slot_service=slot_service,
        session_store=session_store,
    )


def get_reservation_form_service(
    api_client: IReservationApiClient = Depends(get_royal_api),
) -> IReservationFormService:
    """ReservationFormService 인스턴스 생성."""
    return ReservationFormService(api_client=api_client)


def get_chat_orchestrator(
    intent_router: IIntentRouter = Depends(get_intent_router),
    rag_service: IRAGSearchService = Depends(get_rag_search_service),
    reservation_orchestrator: IReservationOrchestrator = Depends(
        get_reservation_orchestrator
    ),
    session_store: SessionStore = Depends(get_redis_session_store),
    llm_client: ILLMClient = Depends(get_llm_client),
) -> IChatOrchestrator:
    """ChatOrchestrator 인스턴스 생성."""
    return ChatOrchestrator(
        intent_router=intent_router,
        rag_service=rag_service,
        reservation_orchestrator=reservation_orchestrator,
        session_store=session_store,
        llm_client=llm_client,
    )
