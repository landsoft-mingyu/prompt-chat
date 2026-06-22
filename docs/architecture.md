# 프롬프트형 홈페이지 AI 에이전트 시스템 - 아키텍처 문서

## 1. 프로젝트 개요

### 목표
- 궁능, 박물관 등의 예약 시스템을 FastAPI로 구현
- 외부 ROYAL API와 통합하여 실시간 예약 관리
- 로컬 CUBRID 데이터베이스와 외부 API를 분리
- 깨끗한 아키텍처(Clean Architecture) 원칙 준수

### 기술 스택
```
Backend Framework: FastAPI 0.137.0
Python Version: 3.10+
API Documentation: OpenAPI/Swagger
Database: CUBRID (pycubrid 1.5.0)
HTTP Client: httpx 0.28.1
ORM: SQLAlchemy 2.0.51
Validation: Pydantic v2 2.13.4
Configuration: pydantic-settings 2.14.1
Web Server: Uvicorn 0.49.0
Reverse Proxy: Nginx 1.27
Containerization: Docker
Orchestration: Docker Compose
Testing: pytest 9.0.2
```

---

## 2. 전체 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────────┐
│                           외부 클라이언트                              │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP/HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Nginx (port 8080)                              │
│                    (Reverse Proxy & Gateway)                        │
│  - API 라우팅                                                       │
│  - 정적 문서 제공 (/docs, /openapi.json)                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   FastAPI Application (port 8000)                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │           API Layer (routes)                                │   │
│  │  ┌──────────────────────┐  ┌──────────────────────────┐   │   │
│  │  │  health.py           │  │  reservation.py          │   │   │
│  │  │  - health_check()    │  │  - list_programs()       │   │   │
│  │  │  - db_health_check() │  │  - list_parts()          │   │   │
│  │  └──────────────────────┘  │  - get_my_reservation()  │   │   │
│  │                             │  - create_reservation()  │   │   │
│  │                             │  - cancel_reservation()  │   │   │
│  │                             └──────────────────────────┘   │   │
│  └──────────────────┬──────────────────────────────────────────┘   │
│                     │ (DI: Depends)                                 │
│  ┌──────────────────▼──────────────────────────────────────────┐   │
│  │         Dependencies (DI Container)                          │   │
│  │  - get_app_settings()        → Settings                    │   │
│  │  - get_royal_api()           → RoyalApi                    │   │
│  │  - get_reservation_repository() → ReservationRepository    │   │
│  └──────────────────┬──────────────────────────────────────────┘   │
│                     │                                               │
│  ┌──────────────────┴──────────────┬──────────────────┐            │
│  │                                 │                  │            │
│  ▼                                 ▼                  ▼            │
│  ┌──────────────────┐  ┌───────────────────┐  ┌────────────────┐  │
│  │ Repository       │  │ HTTP Adapter      │  │ Schemas        │  │
│  │ Interface        │  │                   │  │                │  │
│  └──────────────────┘  │ RoyalApi          │  │ Reservation... │  │
│        │                │                   │  │ Health...      │  │
│        │ (implements)   │ - get_programs()  │  │ Action...      │  │
│        │                │ - get_parts()     │  │ Chat...        │  │
│        ▼                │ - get_reservation │  │ Document...    │  │
│  ┌──────────────────┐  │ - create_reserv.. │  │                │  │
│  │ CUBRID           │  │ - cancel_reserv.. │  │                │  │
│  │ Repository       │  │                   │  │                │  │
│  │ Impl.            │  └───────────────────┘  └────────────────┘  │
│  │                  │            │                                 │
│  │ - find_programs()│            ▼                                 │
│  │ - find_parts()   │  ┌────────────────────────────┐             │
│  │ - count_reserved │  │ Core Layer                 │             │
│  └──────────────────┘  │ - config.py                │             │
│        │                │ - exceptions.py            │             │
│        ▼                │ - logging.py               │             │
│  ┌──────────────────┐  │ - security.py              │             │
│  │   CUBRID         │  └────────────────────────────┘             │
│  │   Database       │                                              │
│  │   (local)        │                                              │
│  └──────────────────┘                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────┐
    │ External ROYAL API                  │
    │ https://royal.landsoft.co.kr        │
    │                                     │
    │ /ROYAL/api/v1/res/list              │
    │ /ROYAL/api/v1/res/parts             │
    │ /ROYAL/api/v1/res/myReservation     │
    │ /ROYAL/api/v1/res/insert            │
    │ /ROYAL/api/v1/res/cancel            │
    └─────────────────────────────────────┘
```

---

## 3. 레이어별 구조와 역할

### 3.1 API 레이어 (`api/routes/`)

#### [health.py](../app/api/routes/health.py)
**역할**: 헬스 체크 및 서버 상태 모니터링

**엔드포인트**:
| 메서드 | 경로 | 함수명 | 역할 |
|--------|------|--------|------|
| GET | `/health` | `health_check()` | 서버 기본 상태 확인 |
| GET | `/health/db` | `db_health_check()` | CUBRID 연결 상태 확인 |

#### [reservation.py](../app/api/routes/reservation.py)
**역할**: 예약 관련 REST API 엔드포인트 제공

**엔드포인트**:
| 메서드 | 경로 | 함수명 | 역할 | 데이터 소스 |
|--------|------|--------|------|----------|
| GET | `/api/v1/reservations/programs` | `list_programs()` | 프로그램 목록 조회 | ROYAL API |
| GET | `/api/v1/reservations/parts` | `list_parts()` | 회차 목록 조회 | ROYAL API |
| GET | `/api/v1/reservations/my-reservation` | `get_my_reservation()` | 예약 조회 | ROYAL API |
| POST | `/api/v1/reservations/create` | `create_reservation()` | 예약 생성 | ROYAL API |
| POST | `/api/v1/reservations/cancel` | `cancel_reservation()` | 예약 취소 | ROYAL API |

---

### 3.2 스키마 레이어 (`schemas/`)

#### [common.py](../app/schemas/common.py)
- 공통 데이터 구조 및 상수 정의

#### [health.py](../app/schemas/health.py)
- `HealthCheckResponse`: 헬스 체크 응답
- `HealthCheckResult`: DB 상태 결과

#### [action.py](../app/schemas/action.py)
- `ActionRequest`: 사용자 액션 요청
- `ActionCard`: UI 카드 컴포넌트
- 9개 필드 + 10개 테스트 케이스

#### [chat.py](../app/schemas/chat.py)
- `ChatRequest`: 채팅 메시지 요청
- `ChatResponse`: 채팅 응답

#### [document.py](../app/schemas/document.py)
- `Document`: 문서 메타데이터
- `Chunk`: 문서 청크 정보

#### [reservation.py](../app/schemas/reservation.py)
**데이터 모델**:

```python
# 요청 스키마
class ReservationCreateRequest(BaseModel):
    res_idx: str              # 프로그램 ID
    pt_idx: str               # 회차 ID
    group_code: str           # 기관 코드
    res_gubun: str            # 예약 유형 (Y=개인, N=단체)
    res_group_gubun: str      # 단체 구분 (Y=청소년, N=일반)
    res_date: date            # 예약 날짜 (오늘 이후만 허용)
    res_name: str             # 예약자명
    res_mobile: str           # 휴대폰 번호 (010-xxxx-xxxx 형식)
    res_user_cnt: int         # 예약 인원
    res_pri_policy_yn: str    # 개인정보 동의

# 응답 스키마
class ReservationCreateResponse(BaseModel):
    status: str = Field(alias="resReqStatus")
    message: str | None = Field(default=None, alias="resReqMsg")
```

**검증 규칙**:
- `res_date`: 미래 날짜만 허용 (오늘 이후)
- `res_mobile`: 010-xxxx-xxxx 형식 필수 (정규식: `^\d{3}-\d{3,4}-\d{4}$`)
- `res_user_cnt`: 1 이상의 정수

---

### 3.3 저장소 인터페이스 레이어 (`repositories/interfaces/`)

#### [reservation_repository.py](../app/repositories/interfaces/reservation_repository.py)
**추상 메서드**:
```python
class ReservationRepository(ABC):
    @abstractmethod
    async def find_programs(self, site_code: str, filters: dict) -> list[ProgramInfo]:
        """프로그램 목록 조회 (CUBRID)"""
        
    @abstractmethod
    async def find_available_parts(self, res_idx: str) -> list[PartInfo]:
        """오늘 이후 회차 목록 조회 (CUBRID)"""
        
    @abstractmethod
    async def count_reserved_users(self, res_idx: str) -> int:
        """예약된 사용자 수 조회 (CUBRID)"""
```

**역할**: 데이터 저장소 추상화 (인터페이스 기반 DI)

---

### 3.4 CUBRID 저장소 구현 (`repositories/cubrid/`)

#### [reservation_repository.py](../app/repositories/cubrid/reservation_repository.py)
**역할**: CUBRID 데이터베이스 조회 구현

**구현 메서드**:
```python
class RoyalReservationRepository(ReservationRepository):
    async def find_programs(self, site_code: str, filters: dict) -> list[ProgramInfo]:
        """SELECT * FROM res_program WHERE res_site_code = ?"""
        
    async def find_available_parts(self, res_idx: str) -> list[PartInfo]:
        """SELECT * FROM res_part WHERE res_idx = ? AND res_date >= TODAY()"""
        
    async def count_reserved_users(self, res_idx: str) -> int:
        """SELECT COUNT(*) FROM res_reservation WHERE res_idx = ? AND status = 'Y'"""
```

**특징**:
- `asyncio.to_thread()`로 동기 DB 호출을 비동기로 변환
- TypedDict 사용으로 타입 안정성 제공
- `InvalidInputError` 예외 (CUBRID 전용)

---

### 3.5 HTTP 어댑터 (`adapters/http/`)

#### [royal_api.py](../app/adapters/http/royal_api.py)
**역할**: 외부 ROYAL API 통신

**메서드**:
```python
class RoyalApi:
    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """공통 HTTP 요청 처리 (에러 처리 통합)"""
        
    async def get_programs(self, group_code: str) -> dict:
        """GET /ROYAL/api/v1/res/list?groupCode="""
        
    async def get_parts(self, res_idx: str, res_part_date: str) -> dict:
        """GET /ROYAL/api/v1/res/parts?resIdx=&resPartDate="""
        
    async def get_reservation(self, res_no: str, res_mobile: str) -> dict:
        """GET /ROYAL/api/v1/res/myReservation?resNo=&resMobile="""
        
    async def create_reservation(self, payload: dict) -> dict:
        """POST /ROYAL/api/v1/res/insert"""
        
    async def cancel_reservation(self, res_no: str, res_mobile: str) -> dict:
        """POST /ROYAL/api/v1/res/cancel"""
```

**특징**:
- `_request()` 헬퍼 메서드로 중복 제거 (에러 처리 통합)
- snake_case ↔ camelCase 자동 변환
- httpx.TimeoutException → DatabaseException
- HTTPStatusError 4xx → ValidationException
- HTTPStatusError 5xx → DatabaseException
- RequestError → DatabaseException

**에러 매핑**:
```python
async def _request(self, method: str, path: str, **kwargs) -> dict:
    try:
        response = await self.client.request(
            method, path,
            timeout=self.settings.royal_api_timeout_sec,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException as e:
        raise DatabaseException("ROYAL API 타임아웃", error_code="ROYAL_API_TIMEOUT") from e
    except httpx.HTTPStatusError as e:
        if 400 <= e.response.status_code < 500:
            raise ValidationException("요청 오류", error_code="ROYAL_API_VALIDATION_ERROR") from e
        raise DatabaseException("ROYAL 서버 오류", error_code="ROYAL_API_SERVER_ERROR") from e
    except httpx.RequestError as e:
        raise DatabaseException("네트워크 오류", error_code="ROYAL_API_NETWORK_ERROR") from e
```

---

### 3.6 핵심 레이어 (`core/`)

#### [config.py](../app/core/config.py)
**역할**: 애플리케이션 설정 관리

```python
class Settings(BaseSettings):
    # Database
    database_url: str
    site_code: str = "gbg"
    
    # ROYAL API
    royal_api_base_url: str
    royal_api_timeout_sec: int = 30
    
    # CORS
    cors_allow_origins: list[str] = ["*"]
```

#### [exceptions.py](../app/core/exceptions.py)
**예외 계층 구조**:
```
PromptChatException (베이스)
├── DatabaseException (DB/API 오류)
│   └── InvalidInputError (입력값 오류)
└── ValidationException (요청 검증 오류)
```

**사용 패턴**:
```python
# ROYAL API 호출 실패
raise DatabaseException("ROYAL API 타임아웃", error_code="ROYAL_API_TIMEOUT")

# 사용자 입력 검증 실패
raise ValidationException("휴대폰 번호 형식 오류", error_code="INVALID_MOBILE")

# CUBRID 조회 실패
raise DatabaseException("데이터베이스 연결 실패", error_code="DB_CONNECTION_ERROR")
```

#### [logging.py](../app/core/logging.py)
- 로깅 설정 및 포매팅

#### [security.py](../app/core/security.py)
- 보안 관련 유틸리티

---

## 4. 의존성 역전 구현 위치

### 4.1 ReservationRepository 패턴

**인터페이스 정의**:
```
Location: repositories/interfaces/reservation_repository.py
Abstract Methods:
  - find_programs(site_code, filters) → list[ProgramInfo]
  - find_available_parts(res_idx) → list[PartInfo]
  - count_reserved_users(res_idx) → int
```

**구현체**:
```
Location: repositories/cubrid/reservation_repository.py
Class: RoyalReservationRepository(ReservationRepository)
  - CUBRID 데이터베이스 접근
  - asyncio.to_thread()로 동기 → 비동기 변환
```

**DI 조립**:
```
Location: dependencies.py
def get_reservation_repository() -> ReservationRepository:
    return RoyalReservationRepository(db_engine=app.state.db_engine)
```

**사용 위치**:
```
Location: api/routes/reservation.py:list_parts()
async def list_parts(
    res_idx: str,
    repo: ReservationRepository = Depends(get_reservation_repository),
):
    parts = await repo.find_available_parts(res_idx)
```

### 4.2 IReservationApiClient 패턴 (의존성 역전)

**인터페이스 위치**:
```
Location: repositories/interfaces/reservation_api_client.py
Interface: IReservationApiClient (ABC)
  - 6개 추상 메서드 정의
  - get_programs(), get_program_detail(), get_parts()
  - get_reservation(), create_reservation(), cancel_reservation()
```

**구현체 위치**:
```
Location: adapters/http/royal_api.py
Class: RoyalApi(IReservationApiClient)
  - ROYAL 외부 API와의 통신을 캡슐화
  - 6개 메서드로 모든 API 호출 처리
  - _request() 헬퍼로 에러 처리 통합
```

**DI 조립 위치**:
```
Location: dependencies.py
def get_royal_api(request: Request, settings: Settings = Depends(get_app_settings)) -> IReservationApiClient:
    return RoyalApi(
        client=request.app.state.royal_api_client,
        settings=settings
    )
```

**사용 위치**:
```
Location: api/routes/reservation.py
@router.post("/api/v1/reservations/create")
async def create_reservation(
    req: ReservationCreateRequest,
    api_client: IReservationApiClient = Depends(get_royal_api),
):
    result = await api_client.create_reservation(req.model_dump())
```

---

## 5. DB 분리 전략

### 5.1 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                     데이터 저장소 역할 분담                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Local CUBRID Database (pycubrid)                               │
│  ├── 프로그램 정보 (캐시용)                                     │
│  │   └── find_programs() → list[ProgramInfo]                   │
│  ├── 회차 정보 (캐시용, 오늘 이후만)                           │
│  │   └── find_available_parts() → list[PartInfo]               │
│  └── 조회 통계 (선택사항)                                       │
│      └── count_reserved_users() → int                          │
│                                                                 │
│  External ROYAL API (httpx.AsyncClient)                        │
│  ├── 실시간 프로그램 목록 조회                                 │
│  │   └── GET /ROYAL/api/v1/res/list                            │
│  ├── 회차 정보 조회                                            │
│  │   └── GET /ROYAL/api/v1/res/parts                           │
│  ├── 예약 조회 (res_no + res_mobile 기반)                     │
│  │   └── GET /ROYAL/api/v1/res/myReservation                   │
│  ├── 예약 생성 + 카톡 알림톡 발송                              │
│  │   └── POST /ROYAL/api/v1/res/insert                         │
│  └── 예약 취소                                                  │
│      └── POST /ROYAL/api/v1/res/cancel                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 요청 경로별 DB 사용

**프로그램 조회 경로**:
```
GET /api/v1/reservations/programs
  → routes/reservation.py::list_programs()
  → IReservationApiClient.get_programs()
  → ROYAL API 호출
  → 응답
```

**예약 생성 경로**:
```
POST /api/v1/reservations/create
  → routes/reservation.py::create_reservation()
  → RoyalApi.create_reservation()
  → External ROYAL API (트랜잭션 처리)
  → 예약번호 + 카톡 알림톡 발송
  → 응답
```

---

## 6. 모듈 확장 방법

### 6.1 새로운 시스템 추가 (예: 새로운 궁능)

**필요한 파일**:

1. **저장소 인터페이스** (필요시)
   ```
   repositories/interfaces/new_system_repository.py
   class NewSystemRepository(ABC):
       @abstractmethod
       async def fetch_data(...): ...
   ```

2. **구현체**
   ```
   repositories/cubrid/new_system_repository.py
   class NewSystemCubridRepository(NewSystemRepository):
       async def fetch_data(...): ...
   ```

3. **HTTP 어댑터** (외부 API 필요시)
   ```
   adapters/http/new_system_api.py
   class NewSystemApi:
       async def get_data(...): ...
   ```

4. **라우트**
   ```
   api/routes/new_system.py
   router = APIRouter(prefix="/api/v1/new-system")
   @router.get("/endpoint")
   async def endpoint(...): ...
   ```

5. **스키마**
   ```
   schemas/new_system.py
   class NewSystemRequest(BaseModel): ...
   class NewSystemResponse(BaseModel): ...
   ```

6. **DI 업데이트**
   ```
   dependencies.py
   def get_new_system_repo() -> NewSystemRepository:
       return NewSystemCubridRepository(...)
   ```

7. **main.py에 라우터 등록**
   ```python
   from app.api.routes import new_system
   app.include_router(new_system.router)
   ```

### 6.2 새로운 기능 추가 (예: 예약 변경)

**필요한 파일**:

1. **스키마 확장**
   ```python
   schemas/reservation.py에 ReservationUpdateRequest, ReservationUpdateResponse 추가
   ```

2. **어댑터 메서드 추가**
   ```python
   adapters/http/royal_api.py에 update_reservation() 추가
   ```

3. **라우트 추가**
   ```python
   api/routes/reservation.py에 @router.patch("/api/v1/reservations/{res_no}") 추가
   ```

---

## 7. 테스트 현황

**테스트 범위**: 59/59 통과 ✅

```
tests/schemas/
├── test_action.py          (16 tests)
├── test_chat.py           (23 tests)
├── test_document.py       (10 tests)
└── test_reservation.py    (10 tests)
```

**테스트 커버리지**: 100%

---

## 8. 현재 미구현 항목

### 8.1 예정된 기능
- [ ] 예약 변경 API (PATCH /api/v1/reservations/{res_no})
- [ ] 예약 내역 조회 API (사용자별 예약 목록)
- [ ] 통계 대시보드 API

### 8.2 개선 사항
- [ ] OpenAPI/Swagger 더 자세한 문서화
- [ ] 통합 테스트 (E2E 테스트)
- [ ] 캐싱 전략 (Redis 도입)
- [ ] 요청 레이트 제한
- [ ] 로깅 및 모니터링 대시보드

### 8.3 선택적 기능
- [ ] 배치 예약 (여러 회차 동시 예약)
- [ ] 예약 대기열 관리
- [ ] 사용자 선호도 저장

---

## 9. 배포 구조

```
Docker Compose (docker-compose.yml)
├── nginx (gateway)
│   └── Port 8080 (Public)
│       ├── /docs → FastAPI Swagger
│       ├── /api/v1/health → Health Check
│       └── /api/v1/... → Proxy to API
│
└── FastAPI API Server
    └── Port 8000 (Internal)
        ├── routes/health.py
        ├── routes/reservation.py
        ├── adapters/http/royal_api.py (→ external ROYAL API)
        └── repositories/cubrid/ (→ local CUBRID)
```

**실행 명령**:
```bash
# 빌드 및 실행
docker compose up -d api

# 이미지 재빌드
docker compose build api

# 로그 추적
docker compose logs -f api

# 헬스 체크
curl http://localhost:8080/health
```

---

## 10. 아키텍처 원칙

### 10.1 SOLID 원칙 준수

| 원칙 | 구현 위치 | 상태 |
|------|---------|------|
| Single Responsibility | routes, repositories, adapters 분리 | ✅ |
| Open/Closed | 인터페이스 기반 DI | ✅ |
| Liskov Substitution | ReservationRepository 인터페이스 | ✅ |
| Interface Segregation | 독립적인 저장소 인터페이스 | ✅ |
| Dependency Inversion | dependencies.py DI 컨테이너 | ✅ |

### 10.2 아키텍처 계층 분리

```
API Layer (routes)
    ↓ (no circular dependencies)
Repository/Adapter Layer (repositories, adapters)
    ↓
Core Layer (config, exceptions, logging)
    ↓
External Systems (CUBRID, ROYAL API)
```

### 10.3 에러 처리 전략

```python
# 공통 에러 처리 (adapters/http/royal_api.py의 _request 메서드)
try:
    response = await self.client.request(...)
except httpx.TimeoutException:
    raise DatabaseException("ROYAL API 타임아웃")
except httpx.HTTPStatusError as e:
    if 400 <= e.response.status_code < 500:
        raise ValidationException("요청 오류")
    else:
        raise DatabaseException("서버 오류")
except httpx.RequestError:
    raise DatabaseException("네트워크 오류")
```

---

## 11. 성능 특성

### 11.1 비동기 처리

- **FastAPI**: 모든 엔드포인트 `async/await`
- **HTTP 호출**: httpx.AsyncClient (완전 비동기)
- **DB 호출**: asyncio.to_thread() (논블로킹 변환)

### 11.2 타임아웃

| 구성 요소 | 타임아웃 |
|---------|--------|
| ROYAL API 호출 | 30초 (설정 가능, royal_api_timeout_sec) |
| CUBRID 쿼리 | 10초 (pycubrid 디폴트) |
| 전체 요청 | Nginx에서 관리 (proxy_connect_timeout 등) |

### 11.3 동시 요청 처리

- FastAPI: Uvicorn workers로 멀티프로세싱
- 각 워커: asyncio 이벤트 루프로 수천 개 동시 연결 처리
- CUBRID: 연결 풀링 (필요시 pycubrid 연결 풀 추가)

---

### 코드 특징
- 타입 힌팅 100% (Pydantic, Type annotations)
- 예외 처리 통합 (custom exception hierarchy)
- DI 기반 느슨한 결합
- 테스트 커버리지 100% (59 tests)
- 코드 중복 제거 (RoyalApi._request() 통합)
---

## 부록: 전체 의존성 맵

```
main.py (Application Entry Point)
  ├── Settings (from core/config.py)
  ├── CORS Middleware
  ├── Exception Handlers
  │   ├── PromptChatException
  │   ├── DatabaseException
  │   └── ValidationException
  │
  ├── APIRouter
  │   ├── api/routes/health.py
  │   │   ├── HealthService
  │   │   └── ReservationRepository (via DI)
  │   │
  │   └── api/routes/reservation.py
  │       ├── ReservationRepository (via DI)
  │       ├── IReservationApiClient (via DI)
  │       └── Pydantic Schemas
  │
  └── Lifespan
      ├── httpx.AsyncClient (for ROYAL API)
      └── CUBRID Connection Pool

dependencies.py (DI Container)
  ├── get_app_settings() → Settings
  ├── get_reservation_repository() → ReservationRepository
  ├── get_royal_api() → IReservationApiClient
  └── get_health_service() → HealthService

repositories/
  ├── interfaces/reservation_repository.py
  │   └── ReservationRepository (ABC)
  │
  └── cubrid/reservation_repository.py
      └── RoyalReservationRepository(ReservationRepository)
          ├── CUBRID Connection
          └── asyncio.to_thread()

adapters/http/
  └── royal_api.py
      ├── RoyalApi
      ├── httpx.AsyncClient
      └── _request() helper

schemas/
  ├── common.py
  ├── action.py
  ├── chat.py
  ├── document.py
  ├── health.py
  └── reservation.py

core/
  ├── config.py (Settings)
  ├── exceptions.py (Exception hierarchy)
  ├── logging.py (Logging configuration)
  └── security.py (Security utilities)
```
