# 코드 리뷰 — 불필요 코드 & FastAPI 공식 문서 기준 검토

> 작성일: 2026-06-16
> 대상: `backend/app/` 전체
> 기준: FastAPI 공식 문서 + 실제 코드 분석

---

## ⚠️ 분류 정정

최초 리뷰에서 "Dead Code"로 묶었던 항목 중 다음은 **미구현 기능을 위한 의도적
스캐폴딩**이며 제거 대상이 아니다 (향후 작업 예정):

- **B-3** CUBRID 예약 경로 (캐싱/통계용 예정)
- **B-4** RAG/챗봇 인터페이스 4종 (chatbot/content/session/vector)
- **B-6** `get_program_detail` (향후 상세 조회 API)
- **B-7** 빈 파일 `core/logging.py`, `core/security.py` (향후 구현)

→ 따라서 "진짜 제거 대상"은 정의·필드가 **중복**이거나 어디에도 연결될 계획이
없는 항목(B-1, B-2, B-8)으로 한정한다.

---

## 처리 결과 (2026-06-16 작업 반영)

| 항목 | 내용 | 상태 |
|------|------|------|
| A-1 | 라우트 `except Exception` 제거 → 전역 핸들러 위임 | ✅ 완료 |
| A-2 | `response_model` 연결 (create/cancel) | ✅ 완료 |
| A-3 | `JSONResponse` import 상단 이동 | ✅ 완료 |
| A-4 | SSL `verify`를 `royal_api_verify_ssl` 설정값으로 분리 | ✅ 완료 |
| B-1 | `LLMConfig` 중복 정의 제거 | ✅ 완료 |
| B-2 | `royal_database_url` 미사용 프로퍼티 제거 | ✅ 완료 |
| B-5 | 미사용 응답 스키마 연결 (create=`ReservationCreateResponse`+`res_no` 확장) | ✅ 완료 |
| B-8 | 미사용 상수 3개 제거 | ✅ 완료 |
| C-1 | `app/interfaces/` → `repositories/interfaces/` 통합 | ✅ 완료 |
| C-4 | ruff `target-version` py310으로 통일 | ✅ 완료 |
| B-3·B-4·B-6·B-7 | 미구현 스캐폴딩 — 보존 | ⏸️ 유지 |

**검증**: 62 tests passed / ruff All checks passed

### B-5 보충 — 일부 스키마는 연결 보류

`ReservationDetail`, `ReservationPart`는 필드가 **snake_case이고 alias가 없어**
ROYAL의 camelCase 응답을 파싱할 수 없다. `response_model`로 연결하면 검증
실패로 **라우트가 깨지므로** 보류했다. 연결하려면 각 필드에 `Field(alias=...)`
추가가 선행되어야 한다 (parts/my-reservation은 현재 pass-through 유지).

---

## 요약 (최초 리뷰 원본)

| 분류 | 항목 수 | 심각도 |
|------|--------|--------|
| FastAPI 공식 기준 수정 필요 | 5 | 🔴 높음 ~ 🟡 중간 |
| 불필요한 코드 (Dead Code) | 8 | 🟡 중간 |
| 구조/일관성 문제 | 5 | 🟡 중간 ~ 🟢 낮음 |
| 사소한 정리 | 3 | 🟢 낮음 |

핵심 결론:
1. **라우트 절반이 전역 예외 핸들러를 무력화**하고 있음 (가장 시급)
2. **`response_model` 누락**으로 OpenAPI 문서/응답 검증 미작동
3. **Python 3.10(로컬) vs 3.11(Docker/ruff)** 버전 불일치로 lint 충돌
4. CUBRID 예약 경로 등은 죽은 코드가 아니라 **미구현 스캐폴딩** (위 정정 참조)

---

## A. FastAPI 공식 문서 기준 — 수정 필요

### A-1. 🔴 라우트의 광범위한 `except Exception`이 전역 예외 핸들러를 무력화

**위치**: [reservation.py](../app/api/routes/reservation.py) — `get_my_reservation`, `create_reservation`, `cancel_reservation`

```python
# 현재 코드
@router.post("/create")
async def create_reservation(req, api_client=Depends(get_royal_api)):
    try:
        result = await api_client.create_reservation(req.model_dump())
        return {...}
    except HTTPException:
        raise
    except Exception as e:               # ← 문제
        raise HTTPException(status_code=503, detail=str(e))
```

**문제점**:
- `main.py`에 `DatabaseException`(503), `ValidationException`(400) 전역 핸들러가 이미 등록되어 있음
- 하지만 `ValidationException`/`DatabaseException`은 `Exception`의 하위 클래스이므로 위 `except Exception`이 **먼저 가로채서** 모두 503으로 변환
- 결과: ROYAL API가 4xx(잘못된 요청)를 반환해도 클라이언트는 503을 받음 → 전역 핸들러가 무의미
- `detail=str(e)`로 **내부 예외 메시지를 그대로 노출** (정보 누출)

**권장 (FastAPI 공식: 예외는 핸들러에 위임)**:
```python
@router.post("/create")
async def create_reservation(req, api_client=Depends(get_royal_api)):
    result = await api_client.create_reservation(req.model_dump())
    return {...}
# try/except 제거 → DatabaseException/ValidationException은 전역 핸들러가 처리
```

---

### A-2. 🟡 라우트에 `response_model` 누락 (`-> dict` 반환)

**위치**: [reservation.py](../app/api/routes/reservation.py) — `list_programs`, `list_parts`, `get_my_reservation`, `create_reservation`

```python
@router.get("/programs")
async def list_programs(...) -> dict:   # ← response_model 없음
    return await api_client.get_programs(group_code)
```

**문제점**:
- FastAPI 공식 문서는 `response_model` 지정을 권장 — 응답 검증·직렬화·OpenAPI 스키마 생성의 기준
- `dict` 반환은 Swagger 문서에 응답 구조가 표시되지 않고, 응답 필터링/검증이 동작하지 않음
- 이미 `ReservationCreateResponse`, `ReservationDetail` 스키마를 정의해 두고도 사용하지 않음 (B-5 참조)

**권장**: 정의된 스키마를 `response_model`로 연결하거나, 외부 API 응답을 그대로 패스스루할 경우 명시적 응답 스키마를 추가.

---

### A-3. 🟡 예외 핸들러 내부의 반복 임포트

**위치**: [main.py:69,80,91](../app/main.py)

```python
@app.exception_handler(DatabaseException)
async def database_exception_handler(_request, exc):
    from fastapi.responses import JSONResponse   # ← 핸들러마다 반복
    return JSONResponse(...)
```

**권장**: `from fastapi.responses import JSONResponse`를 파일 최상단으로 이동. 함수 내부 임포트는 순환참조 회피 목적이 아니면 불필요.

---

### A-4. 🟡 `httpx.AsyncClient(verify=False)` — SSL 검증 비활성화

**위치**: [main.py:35](../app/main.py)

```python
app.state.royal_api_client = httpx.AsyncClient(
    base_url=settings.royal_api_base_url,
    timeout=httpx.Timeout(settings.royal_api_timeout_sec),
    verify=False,   # ← MITM 취약
)
```

**문제점**: SSL 인증서 검증을 끄면 중간자 공격에 노출됨. 내부망 사설 인증서 때문이라면 **CA 번들을 명시**하는 것이 정석.

**권장**:
```python
verify="/path/to/internal-ca.pem"   # 사설 CA 경로 지정
# 또는 최소한 설정값으로 분리: verify=settings.royal_api_verify_ssl
```

---

### A-5. 🟢 CORS 설정 — `allow_credentials=True` + 와일드카드 조합 주의

**위치**: [main.py:56-62](../app/main.py)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,  # 기본값 명시적 origin → OK
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**참고**: 현재는 `cors_allow_origins`가 명시적(`localhost:3000`)이라 안전. 단, 운영에서 `allow_origins=["*"]`로 바꾸면서 `allow_credentials=True`를 유지하면 브라우저가 요청을 거부함(스펙상 금지 조합). 운영 배포 시 주의 필요.

---

## B. 불필요한 코드 (Dead Code)

### B-1. 🟡 `LLMConfig` 클래스 전체 미사용

**위치**: [config.py:11-28](../app/core/config.py)

`LLMConfig` 클래스가 정의되어 있으나 어디서도 사용되지 않음. 게다가 `Settings` 클래스가 동일한 LLM 필드(`llm_base_url`, `llm_model`, `llm_api_key`, `llm_timeout_sec`)를 **중복 정의**하고 있음.
→ `LLMConfig` 삭제, 또는 `Settings`가 `LLMConfig`를 포함하도록 일원화.

### B-2. 🟡 `Settings.royal_database_url` 프로퍼티 미사용

**위치**: [config.py:88-94](../app/core/config.py) — 어디서도 호출되지 않음.

### B-3. 🟡 CUBRID 예약 경로 전체가 죽은 코드

다음이 모두 **연결되지 않은 채** 존재:
- 인터페이스: [reservation_repository.py](../app/repositories/interfaces/reservation_repository.py) (`ReservationRepository`)
- 구현체: [cubrid/reservation_repository.py](../app/repositories/cubrid/reservation_repository.py) (`RoyalReservationRepository`)
- DI: [dependencies.py:46](../app/dependencies.py) (`get_reservation_repository`)

→ 어떤 라우트도 `get_reservation_repository`를 주입받지 않음 (모든 예약은 ROYAL API 경유).
**결정 필요**: ① 향후 캐싱/통계 용도로 보존할지, ② 현재 미사용이므로 제거할지. 보존한다면 `# 향후 사용 예정` 주석 명시 권장.

### B-4. 🟡 미사용 인터페이스 4종

**위치**: `repositories/interfaces/`
- `chatbot_repository.py` (`ChatbotRepository`)
- `content_repository.py` (`ContentRepository`)
- `session_store.py`
- `vector_repository.py`

→ 어디서도 import되지 않음. RAG/챗봇 기능의 사전 설계 흔적으로 보임. 미구현 기능이면 별도 브랜치/문서로 관리하고 메인에서는 제거 검토.

### B-5. 🟡 미사용 스키마 4종

**위치**: [schemas/reservation.py](../app/schemas/reservation.py)
- `ReservationCreateResponse`, `ReservationDetail`, `ReservationPart`, `ReservationQueryRequest` 모두 라우트에서 미사용.
→ A-2(`response_model`)와 연계해 실제 연결하거나 제거.

### B-6. 🟢 `get_program_detail` — 라우트 없음

**위치**: 인터페이스+구현 모두 존재하나 노출 라우트 없음. 의도적 API 표면이면 유지, 아니면 제거.

### B-7. 🟢 빈 파일 2개

`core/logging.py`, `core/security.py` → 0 byte. 아키텍처 문서에는 "로깅 설정", "보안 유틸리티"로 기재되어 있으나 실제 내용 없음. 구현하거나 문서에서 제외.

### B-8. 🟢 미사용 상수

**위치**: [cubrid/reservation_repository.py:13-15](../app/repositories/cubrid/reservation_repository.py)
`_DEFAULT_PARTS_LIMIT`, `_RESERVATION_STATUS_PENDING`, `_RESERVATION_STATUS_CANCELLED` 모두 미사용.

---

## C. 구조 / 일관성 문제

### C-1. 🟡 인터페이스 디렉토리가 2곳으로 분산

- `app/interfaces/health_repository.py` (`IHealthRepository`)
- `app/repositories/interfaces/*.py` (`ReservationRepository`, `IReservationApiClient` 등)

→ 동일 역할(인터페이스)이 두 위치에 나뉘어 있어 혼란. 한 곳으로 통일 권장 (예: `repositories/interfaces/`).
또한 네이밍도 혼재: `IHealthRepository`/`IReservationApiClient`(I 접두사) vs `ReservationRepository`(접두사 없음). 컨벤션 통일 필요.

### C-2. 🟡 인터페이스 ↔ 구현 반환 타입 불일치

**위치**: 인터페이스는 `list[dict[str, Any]]`, 구현은 `list[ProgramInfo]`(TypedDict) 반환.
```python
# interface
async def find_programs(...) -> list[dict[str, Any]]: ...
# impl
async def find_programs(...) -> list[ProgramInfo]: ...
```
→ TypedDict로 인터페이스 시그니처도 통일하면 타입 안정성 향상.

### C-3. 🟢 인터페이스 docstring 오류

**위치**: [reservation_repository.py:12](../app/repositories/interfaces/reservation_repository.py)
```python
"""예약 저장소 추상 클래스. 예약 조회/생성/취소 담당. ..."""
```
→ 실제로는 **조회만** 담당(생성/취소는 ROYAL API). docstring 정정 필요.

### C-4. 🟢 Python 3.10(로컬) vs 3.11(Docker/ruff) 버전 불일치

- `pyproject.toml`: `target-version = "py311"`
- `Dockerfile`: `python:3.11-slim`
- 로컬 개발 환경: **Python 3.10.12**

→ ruff가 `UP042`(StrEnum 사용 권장), `UP017`(datetime.UTC 사용 권장)을 띄우지만, 이들은 **3.11+ 전용 문법**이라 로컬 3.10에서 적용 시 `ImportError` 발생. 현재 11개 ruff 경고가 이 충돌에서 발생 중.
**권장**: 로컬 개발 환경을 3.11로 통일하거나, `target-version = "py310"`으로 낮춰 lint 기준을 런타임과 일치시킬 것.

### C-5. 🟢 `InvalidInputError`의 불필요한 `pass`

**위치**: [cubrid/reservation_repository.py:18-21](../app/repositories/cubrid/reservation_repository.py)
```python
class InvalidInputError(ValueError):
    """입력 데이터 검증 실패."""
    pass   # ← docstring 있으면 pass 불필요
```

---

## D. 사소한 정리

### D-1. 🟢 `main.py` 모듈 레벨 `settings` 중복 호출

[main.py:23](../app/main.py)(lifespan 내부)와 [main.py:55](../app/main.py)(모듈 레벨)에서 각각 `get_settings()` 호출. `lru_cache` 덕분에 동작은 정상이나, CORS 설정도 lifespan/팩토리로 모으면 더 일관적.

### D-2. 🟢 `exceptions.py` 자식 클래스의 단순 위임 `__init__`

**위치**: [exceptions.py](../app/core/exceptions.py)
`DatabaseException`, `ValidationException`의 `__init__`이 단지 기본 `error_code`만 바꿔 super 호출. 클래스 속성으로 단순화 가능:
```python
class DatabaseException(PromptChatException):
    """데이터베이스 관련 예외."""
    def __init__(self, message: str, error_code: str = "DATABASE_ERROR"):
        super().__init__(message, error_code)
# → 현 구조도 무방. 통일성만 확인.
```

### D-3. 🟢 자명한 주석 잔존

`# Enum으로 정의하여 타입 안정성 확보`, `# 조회`, `# 상세 조회` 등 코드에서 바로 읽히는 주석 다수. 가독성에 큰 영향은 없으나, 코드와 중복되는 주석은 정리 대상.

---

## 우선순위별 권장 조치

| 순위 | 항목 | 액션 |
|------|------|------|
| 1 | A-1 | 라우트 `try/except Exception` 제거 → 전역 핸들러 위임 |
| 2 | C-4 | Python 버전 통일 (3.10 또는 3.11) — lint 충돌 해소 |
| 3 | A-2 / B-5 | `response_model` 연결 + 미사용 스키마 정리 |
| 4 | B-3 / B-4 | 죽은 CUBRID 경로·미사용 인터페이스 제거 또는 보존 의도 명시 |
| 5 | A-3 / A-4 | 임포트 정리 + SSL 검증 정책 결정 |
| 6 | B-1·B-2·B-7·B-8 | 미사용 클래스/프로퍼티/빈 파일/상수 제거 |
| 7 | C-1·C-2·C-3·D-* | 구조 통일 및 주석/docstring 정리 |

---

## 잘 구현된 점 (유지 권장)

- ✅ `lifespan` 컨텍스트 매니저로 리소스 관리 (FastAPI 최신 권장 방식)
- ✅ `IReservationApiClient` 인터페이스 기반 의존성 역전
- ✅ `_request()` 헬퍼로 HTTP 에러 처리 중앙화
- ✅ `get_settings()`에 `@lru_cache` 적용
- ✅ `health.py` 라우트는 `response_model`·세분화된 예외 처리 적용 (모범 사례)
- ✅ Pydantic 검증 + 스키마 테스트 59건 100% 통과
