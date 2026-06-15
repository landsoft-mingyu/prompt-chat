# 프로젝트 구조

## 전체 레이아웃

```
prompt_chat/
├── docker-compose.yml          # gateway(nginx) + api 컨테이너 구성
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── main.py             # FastAPI 앱 생성, lifespan, 라우터 등록
        ├── dependencies.py     # DI 팩터리 함수 (Depends 체인)
        │
        ├── core/               # 앱 전역 설정 및 공통 유틸
        │   ├── config.py       # 환경변수 → Settings 객체 (pydantic-settings)
        │   ├── exceptions.py   # 커스텀 예외 (미구현)
        │   ├── logging.py      # 로깅 설정 (미구현)
        │   └── security.py     # 인증/보안 (미구현)
        │
        ├── interfaces/         # 추상 인터페이스 (DIP)
        │   └── health_repository.py  # IHealthRepository (Protocol)
        │
        ├── adapters/           # 외부 시스템 연결 구현체
        │   └── db/
        │       └── cubrid.py   # CubridClient — SQLAlchemy로 CUBRID 쿼리 실행
        │
        ├── repositories/       # DB 접근 계층 (interfaces 구현)
        │   └── health_repository.py  # HealthRepository
        │
        ├── services/           # 비즈니스 로직 계층
        │   └── health_service.py     # HealthService
        │
        ├── api/
        │   └── routes/         # 라우터 (엔드포인트 정의)
        │       └── health.py   # GET /health, GET /health/db
        │
        └── schemas/            # Pydantic 요청/응답 스키마
            ├── common.py       # 공통 스키마 (미구현)
            └── health.py       # HealthResponse, DBHealthResponse
```

## 요청 흐름

```
클라이언트
  │ HTTP :3001
  ▼
gateway (nginx)
  │ proxy_pass :8000
  ▼
api (FastAPI)
  │
  ├── routes/health.py         라우터
  │     │ Depends
  ├── dependencies.py          DI 체인 조립
  │     │                        get_db_engine  → app.state.db_engine (싱글턴)
  │     │                        get_cubrid_client
  │     │                        get_health_repository
  │     │                        get_health_service
  │     │
  ├── services/health_service.py   비즈니스 로직
  │     │ IHealthRepository (Protocol)
  ├── repositories/health_repository.py   DB 접근
  │     │ run_in_threadpool (pycubrid = sync 드라이버)
  └── adapters/db/cubrid.py    SQLAlchemy 쿼리 실행
```

## 레이어별 의존 방향

```
routes → services → interfaces ← repositories → adapters
                        ↑
                   (DIP: 서비스는 구체 구현체를 모름)
```

## 엔드포인트

| Method | Path        | 설명               |
|--------|-------------|--------------------|
| GET    | /health     | API 서버 생존 확인 |
| GET    | /health/db  | DB 연결 확인       |

## 환경변수 (docker-compose → Settings)

| 변수            | 예시값          |
|-----------------|-----------------|
| CUBRID_HOST     | 192.168.12.55   |
| CUBRID_PORT     | 33000           |
| CUBRID_DB       | royal           |
| CUBRID_USER     | royal           |
| CUBRID_PASSWORD | royal13!#       |
