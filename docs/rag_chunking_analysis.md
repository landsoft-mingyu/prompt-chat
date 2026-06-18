# RAG 청킹 설계 분석 문서 (site_chunks) — v2 (레이아웃 기반 / 하이브리드 소스)

> 대상 테이블: `cms_board`, `cms_menu_contents`, `ry_info_loca` (ROYAL DB @ 192.168.12.55)
> 목적: Milvus 적재용 **레이아웃 인지(layout-aware) 청킹** 설계
> 작성 기준: **DB 원본 직접 조회 + 기존 JSON 추출본 대조** 결과. 추측 배제.
>
> **결정 사항(확정):**
> - **소스 = 하이브리드** — DB 원본 HTML(`bd_content`/`mc_content`) + strip 텍스트(`bd_content_text`) + 컬럼 메타(`bc_id`/`group_code`/주소 등)를 함께 추출.
> - **범위 = 현재 JSON 범위 유지** — board 150 / menu 49 / ry 25 행만 적재(전체 7,577/1,114/28이 아님).

---

## 0. v1 → v2 가장 중요한 정정

| 항목 | v1 (JSON만 봤을 때) | v2 (DB 확인 후) |
|---|---|---|
| 레이아웃 정보 | "없음(평문)" | **원본 HTML에 살아있음** (`bd_content`, `mc_content`) |
| `bc_id` | "존재하지 않음" | **존재** — content_type의 정답 키 |
| 표 | "깨진 평문, regex로 추정 복원" | **`<table>` 태그로 정확 분리 가능** |
| 섹션 | "키워드 휴리스틱" | **HTML 탭/제목 구조로 정확 분리** |
| JSON `content` 출처 | (원본인 줄 알았음) | `bd_content_text` = **HTML을 strip한 손실본** |

**핵심:** 현재 `rag/*.json`은 원본 HTML을 평문으로 뭉갠 **손실 추출본**이었다. 레이아웃 청킹은 가능할 뿐 아니라, 일부 메뉴는 **이미 HTML 탭 단위로 분할(`_t01`,`_t02`…)** 되어 있었다.

---

## 1. DB 원본 구조 (실측)

### 1.1 cms_board (게시판)
- 전체 `delyn='N'` 행: **7,577** (현재 JSON은 이 중 150건)
- 본문 컬럼이 **2개**:
  - `bd_content` VARCHAR(1G) — **원본 HTML**
  - `bd_content_text` VARCHAR(1G) — HTML strip 텍스트 (← JSON `content`의 출처)
- `bd_htmlyn` CHAR(1) — HTML 여부. 전체 분포: `Y` 833 / `N` 6121 / NULL 623
- **`bc_id`** VARCHAR(150) — 게시판 종류(=content_type 후보):
  `notice01`(4399), `storyBoard`(716), `normal2`(1304), `normal1`(705), `qna`(213), `video02`(125), `board04`(63), `magazine`(39), `sr`(9), `videoVr`(3), `instructions1`(1)
- `bd_notice`(공지 플래그), `group_code`, `bd_title`, `regdt`/`upddt`, `bd_thumb1~3`, `bd_writer` 등.
- `<table>` 포함 행: 294 / 7,577.

**현재 JSON 150건의 정체 (PK=bd_idx로 100% 매칭 확인):**
- 전부 `bc_id='storyBoard'`, **전부 `bd_htmlyn='Y'` (150/150 HTML)**, `group_code=NULL`.
- 즉 우리 범위는 **궁능소개 스토리(storyBoard) HTML 게시글**.

### 1.2 cms_menu_contents (메뉴 본문)
- 전체 `delyn='N'` 행: **1,114** (JSON 49건)
- 본문: `mc_content` VARCHAR(1G) — **HTML**. `<table>` 포함 781 / 1,114.
- 자체 컬럼엔 title/menu_path 없음 → `menu_code`로 `cms_menu` 조인하여 제목/경로 도출
  (`cms_menu.menu_name`=제목, `menu_pfullname`/`menu_navi`=경로). **`menu_code`는 비고유**(여러 페이지 공유).
- 원본 HTML은 시맨틱 구조 사용: `<div class="sub_con_section">`, `class="palace_intro_wrap"`, `class="*_tit"`, `<table class="bd_table">` 등.

**JSON 49건의 정체 (PK=mc_idx 매칭):**
- **40건은 `mc_idx` 직접 매칭.**
- **9건은 `{mc_idx}_t01`,`_t02`… 합성 id** — 베이스 2개 행이 HTML 탭으로 분할된 것:
  - `20231027163702339239` (조선왕릉전시관, 31,603자, `<ul class="royal_tomb_tab tab_menu"><li data-tab="royal_tomb01">조선왕릉전시관</li><li data-tab="royal_tomb02">역사문화관</li>`) → 탭/갤러리 단위로 `_t01~_t04` 분할.
  - `20231102173356170003` (왕의생애, 39,035자, `<div class="sub_con_tab tab_menu">…data-tab="tab01">세자책봉…`) → `_t01~_t05` 분할.
- → **이전 추출기가 이미 레이아웃(탭) 기반 청킹을 수행**했다는 직접 증거. 우리 설계는 이를 정식화·확장하면 됨.

### 1.3 ry_info_loca (위치/교통)
- 전체 행: **28** (JSON 25건, PK=il_idx 100% 매칭)
- 구조정보가 **컬럼으로 정규화**되어 있음: `addrs`, `tel_no`, `tel_fax`, `loca_url`, `group_code`, `title`.
- `content` VARCHAR(1G) — 본문(교통/주차). HTML 태그는 거의 없고 **대체로 평문**.

---

## 2. 하이브리드 추출 사양 (범위 = 현재 JSON 행)

> 동일 행 재현은 **JSON의 `id` → PK** 로 SELECT (범위 정확 보장). 신규 컬럼만 보강.

### 2.1 cms_board (150행, `bd_idx IN (...150 ids)`)
| 추출 컬럼 | 용도 |
|---|---|
| `bd_idx` | source_id (PK) |
| `bc_id` | **content_type 분류** (현 범위 전부 `storyBoard`) |
| `bd_title` | title |
| `bd_content` (HTML) | **레이아웃 청킹 입력** |
| `bd_content_text` | 평문 fallback / 검증용 대조 |
| `bd_htmlyn` | 파서 분기 (Y=HTML / N=평문) |
| `bd_notice`, `group_code`, `bd_writer`, `bd_thumb1~3` | metadata |
| `regdt`, `upddt` | 날짜 |
- `menu_path`/`title`/`site_code`는 기존 JSON 값 보존(추출 시 curated) + 위 컬럼으로 보강.

### 2.2 cms_menu_contents (49 논리 페이지 = 40 직접 + 9 탭분할)
- 40건: `mc_idx` 직접 SELECT → `mc_content` 사용.
- 9건: 베이스 `mc_idx`(`_tNN` 제거) SELECT → **탭(`tab_menu`/`tab_con`, `data-tab`) 단위로 분할**, 탭 라벨을 `section_title`/경로 leaf로. (기존 JSON의 menu_path가 이미 탭 라벨을 반영하므로 그 매핑을 기준으로 정렬.)
- title/menu_path: `cms_menu` 조인(또는 기존 JSON 메타 보존). `menu_code`는 filter scalar(비고유 주의).

### 2.3 ry_info_loca (25행, `il_idx IN (...)`)
| 추출 컬럼 | 용도 |
|---|---|
| `il_idx` | source_id |
| `title` | 위치명 |
| `addrs`, `tel_no`, `tel_fax`, `loca_url` | 위치 scalar/metadata |
| `group_code` | 관리권역 filter |
| `content` | 교통/주차 본문(대체로 평문) |

---

## 3. 레이아웃 인지 청킹 설계 (핵심)

### 3.1 공통 원칙
1. **소스 분기:** `bd_htmlyn='Y'` 또는 본문에 태그 존재 → **HTML 파서 경로**. 아니면 → **평문 fallback 경로**(v1의 문단/키워드 휴리스틱).
2. **HTML → DOM 파싱**(BeautifulSoup/lxml/selectolax). 글자 수가 아니라 **DOM 구조**로 자른다.
3. **보존 1순위:** 시간/요금/요일/전화번호/URL/주소/날짜/한자 병기 → 절대 삭제 금지.
4. **표는 글자수로 자르지 않는다.** `<table>`을 **Markdown 표(또는 `헤더: 값` 행)** 로 재구성해 한 chunk로.
5. 모든 chunk는 원문 추적 가능: `parent_id`(=행), `source_id`(=PK), 필요 시 `dom_path`/`tab_key`.

### 3.2 헤더 위계 (중요 — `<h1~h6>` 아님, 클래스 기반)

**실측: `<h1>~<h6>` 태그는 0개.** 헤더/뎁스는 **CSS 클래스 이름**으로 인코딩됨. DOM 중첩 뎁스(메뉴 최대 13단계)는 대부분 레이아웃 래퍼 노이즈이므로 **원시 뎁스를 위계로 쓰지 않는다.** 아래 **클래스→레벨 매핑**으로 의미 위계를 도출:

**클래스 전수 조사(범위 42개 menu 행, 빈도):**

| 역할 | 클래스(빈도) | 처리 |
|---|---|---|
| L0 탭 | `tab_link`(18), `tab_con`(27), `swiper-slide`(29, 탭 슬라이드) | 섹션 경계, 탭 라벨=`header_path[0]` |
| L1 섹션제목 | `txt_section_tit`(93), `page_privacy_tit`(41), `history_con_tit`, `gallery_tit` | 새 섹션 시작, `header_path` push |
| L2 하위제목 | `info_tit`(26), `tit`(19), `img_info_tit`, `plan_list_tit` | 하위 경계 |
| 섹션 래퍼 | `sub_con_section`(136), `txt_section`(34), `palace_intro_wrap`(14), `info_box_wrap`(44) | 콘텐츠 컨테이너 |
| 표 | `table`/`bd_table`/`bd`(55), `table_wrap`(35), `th_c`(헤더셀) | 표 chunk(`is_table`) |
| 목록 | `list`(146), `list_wrap`(68), `dot_item`(243), `item`(502), `dot`(188) | 묶어서 1 chunk |
| 시간셀 | `time_gray`(233)/`time_red`(81)/`time_blue`(64) | 해설 시간표 색상셀 — **값 보존**(색=언어/유형 의미) |
| **제거** | `sr_only`(223), `hidden`(19), `swiper-button-*`, `style`/`<img>` | 접근성/장식 텍스트 → 드롭(중복·노이즈) |

- L1 섹션 제목은 문서 상단 목차와 일치(예: `경복궁 정규해설 / 경회루 특별관람 해설 / 칠궁 정규해설`) → 신뢰도 높음.
- 표 55개, 목록 177개, 탭(`data-tab`) 18개 확인 — 전부 레이아웃 경계로 활용 가능.
- `sr_only`(screen-reader 전용, "현재 선택됨" 등)·`hidden`은 본문 중복/노이즈이므로 **반드시 제거**.
- 각 chunk에 **breadcrumb `header_path`** 부여: `[탭] > [L1] > [L2]` (예: `왕의생애 > 세자책봉`, `경복궁 정규해설 > 관람방법`). `chunk_text`의 `[섹션]`과 metadata `header_path`에 동시 반영.
- **board(storyBoard)는 제목 클래스 없는 평탄 산문**(뎁스 0~4, 거의 `<p>`) → 위계 없음, 글 제목 + 문단 분할만.
- 클래스 목록은 신규 페이지에서 확장될 수 있으므로 **매핑 테이블을 설정값으로 외부화**(하드코딩 지양).

### 3.3 HTML 경로 분할 우선순위
1. **탭 단위 (L0):** `ul.tab_menu > li.tab_link[data-tab]` + `div.tab_con[data-tab]` 매칭. 탭 라벨 = 섹션. (조선왕릉전시관/왕의생애 케이스.)
2. **L1 섹션 제목:** `*_section_tit`/`*_tit`(L1 매핑) 출현 시 새 섹션 시작, `header_path` push.
3. **L2 하위 제목:** `info_tit` 등 → 하위 경계, `header_path`에 누적.
4. **표:** `<table>` 1개 = 표 chunk 1개(`is_table=true`). `caption`/직전 L1·L2 제목을 `section_title`로. 큰 표는 **행(`<tr>`) 의미 단위**로만 분할하고 헤더(`<th>`) 재첨부.
5. **목록:** `<ul>/<ol>` 블록은 항목들을 묶어 한 chunk(과분할 금지).
6. **정리(clean):** `style`/`<img>`/장식 `<span>` 제거하되 **`alt`/`title` 텍스트는 보존**, 텍스트·수치는 유지. `<!-- … -->` 주석 제거.

### 3.4 평문 경로 (fallback, `htmlyn='N'`/태그 없음)
- v1 규칙 유지: `\n\n` 문단 분할, 섹션 키워드 헤더(`관람방법`/`문의`/`시작`/`소요시간`/`예약`/`요금` 등), 표 캡션 잔재(`… 안내 테이블 - … 로 구성`) 마커.
- 짧은 문서(≤1,000자)는 1 chunk 유지.

### 3.5 테이블별 적용
- **cms_board (전부 storyBoard·HTML):** 글 하나 = parent. HTML 제목/문단/표 기준 분할. 대개 산문이라 1~소수 chunk. content_type=`story`.
- **cms_menu_contents:** 탭→섹션→표 순 분할. 관람시간/요금/해설시간표는 표 chunk로 독립. content_type은 menu_path 카테고리 + 표 성격.
- **ry_info_loca:** 본문 평문 → 교통/주차 섹션 분리 + **위치개요 chunk(주소/좌표/연락 합성)** 필수 생성. content_type=location/transportation/parking.

---

## 4. chunk_id / parent_id 규칙

- `parent_id = {site_code}:{source_table}:{source_id}` (안정적, PK 기반)
- `chunk_id  = {site_code}:{source_table}:{source_id}:{chunk_index:04d}`
  - 예) `ROYAL:cms_menu_contents:20231218092005628534:0001`
- **탭 분할 행**은 `source_id`에 탭 키 보존: `ROYAL:cms_menu_contents:20231102173356170003_t01:0001`
  (기존 JSON의 `_tNN` 규칙과 호환 유지)
- `menu_code`는 **비고유**이므로 id 구성요소로 쓰지 않음(filter scalar 전용).

---

## 5. content_type 체계 (DB 라벨 기반으로 재정의)

> bc_id(게시판) / menu_path(메뉴) / 컬럼(위치) 라벨을 1차 근거로 사용. 현재 **범위 한정** 값은 표기.

| content_type | source | 분류 기준 | 현 범위 |
|---|---|---|---|
| `story` | cms_board | `bc_id='storyBoard'` | **150건 전부** |
| `notice` | cms_board | `bc_id='notice01'` 또는 `bd_notice≠0` | (범위 외, 확장 대비) |
| `magazine`/`video`/`qna` | cms_board | `bc_id` 매핑 | (범위 외) |
| `palace_intro` | menu | menu_path 2seg=`궁능소개` | ✔ |
| `visit_hours` | menu | leaf=`관람시간` | ✔ (표) |
| `visit_fee` | menu | leaf=`관람요금` | ✔ (표) |
| `visit_rules` | menu | leaf=`관람규칙` | ✔ |
| `commentary_guide` | menu | path=`해설안내` 비표 | ✔ |
| `commentary_schedule` | menu | path=`해설안내` 표 | ✔ (표) |
| `reservation_guide` | menu | 2seg=`통합예약`(절차안내) | ✔ (실시간 데이터 아님) |
| `event_schedule` | menu | 2seg=`행사마당` | ✔ |
| `org_intro` | menu | 2seg=`기관소개` | ✔ |
| `culture_story` | menu | 2seg=`자료마당` | ✔ |
| `location_overview` | ry | 주소/좌표 합성 | ✔ |
| `transportation` | ry | 지하철/버스/도보 | ✔ |
| `parking` | ry | 자가용/주차 | ✔ |
| `contact` | ry/menu | tel/문의 | ✔ |
| `generic_content` | 전체 | fallback | — |

`source_type`(대분류): `article`(board) / `menu_page`(menu) / `location`(ry).
**bc_id를 별도 scalar로도 보존** → 게시판 종류 필터 가능.

---

## 6. Milvus collection schema (`site_chunks`) — v2

| 필드 | 타입 | nullable | 위치 | filter | 비고 |
|---|---|---|---|---|---|
| `chunk_id` | VARCHAR PK | ✗ | scalar | ✅ | `{site}:{table}:{id}:{idx}` |
| `parent_id` | VARCHAR | ✗ | scalar | ✅ | 원문 행 |
| `site_code` | VARCHAR | ✗ | scalar | ✅ | 멀티사이트 |
| `source_table` | VARCHAR | ✗ | scalar | ✅ | 테이블 |
| `source_id` | VARCHAR | ✗ | scalar | ✅ | PK(탭키 포함) |
| `source_type` | VARCHAR | ✗ | scalar | ✅ | article/menu_page/location |
| `content_type` | VARCHAR | ✗ | scalar | ✅ | 5장 enum |
| `bc_id` | VARCHAR | ✅ | scalar | ✅ | **게시판 종류(신규)** |
| `menu_code` | VARCHAR | ✅ | scalar | ✅ | 비고유 |
| `menu_path` | VARCHAR | ✅ | scalar | △ | 경로 |
| `group_code` | VARCHAR | ✅ | scalar | ✅ | ry 관리권역(신규) |
| `title` | VARCHAR | ✅ | scalar | △ | 제목/위치명 |
| `section_title` | VARCHAR | ✅ | scalar | ✗ | 현재 chunk의 섹션명(말단) |
| `header_path` | VARCHAR | ✅ | scalar | ✗ | breadcrumb `탭>L1>L2`(클래스 위계, 신규) |
| `is_table` | BOOL | ✗ | scalar | ✅ | 표 chunk |
| `html_yn` | CHAR | ✅ | scalar | △ | 소스 경로(신규) |
| `chunk_text` | VARCHAR | ✗ | scalar | ✗ | **임베딩 대상 정제문** |
| `text_hash` | VARCHAR | ✗ | scalar | ✅ | 멱등/중복 |
| `regdt`/`upddt` | VARCHAR | ✅ | scalar | △ | 날짜 |
| `metadata` | JSON | ✗ | json | ✗ | writer/thumb/addrs/tel/loca_url/lat·lng/탭키 등 |
| `embedding` | FLOAT_VECTOR | ✗ | vector | ANN | chunk_text 임베딩 |

- ry의 `addrs/tel_no/tel_fax/loca_url/latitude/longitude`는 metadata JSON 보존(향후 geo 필요 시 scalar 승격).
- 임베딩 차원/메트릭은 모델 선정 후 확정.

---

## 7. chunk_text 생성 규칙

prefix 5줄 + 본문 (노이즈 최소화):
```
[사이트] ROYAL
[메뉴] >궁능유적본부>관람안내>해설안내>경복궁
[제목] 경복궁
[섹션] 경복궁 정규해설 시간표
[본문]
{HTML→정제 텍스트 / 표는 Markdown 표}
```
- title/menu_path/section_title은 prefix로 부착(검색 정합 ↑). `writer/thumb/menu_code/bc_id` 등 필터값은 **본문에 넣지 않음**(scalar/metadata로만).
- **표는 Markdown으로 재구성**(사람·임베딩 모두 가독): `| 언어 | 요일 | 시간 |` 형태. 셀 복원 불가 시 원문 보존.
- 전화/URL/시간/요금/날짜 보존.
- ry 위치개요 chunk는 컬럼을 자연어 합성: `[제목]…[주소] addrs [문의] tel_no [본문] content`.

---

## 8. 청킹 알고리즘 (단계별)

| 단계 | 입력 | 처리 | 출력 | fallback |
|---|---|---|---|---|
| 1 추출 | JSON id 목록 | PK로 DB SELECT(HTML+메타) | 행 레코드 | 누락행 로그 |
| 2 정규화 | 행 | 필드 표준화, 탭키 분리(`_tNN`) | norm doc | 필수 누락 skip |
| 3 소스분기 | htmlyn/태그 | HTML/평문 경로 선택 | 경로 플래그 | 불명 → 평문 |
| 4 DOM 파싱 | HTML | 탭/섹션/표/목록 트리화 | DOM 노드 | 파싱 실패 → 평문 경로 |
| 5 섹션 분할 | DOM | 탭→시맨틱→제목→표 순 | section[] | 노드 없음 → 문단 |
| 6 표 처리 | table 노드 | Markdown 표 재구성 | table chunk | 복원 실패 → 원문 |
| 7 chunk 생성 | section[] | 크기 규칙(표 비분할 우선) | chunk[] | 과대 → 문장/길이 |
| 8 chunk_text | chunk+meta | prefix 합성 | chunk_text | — |
| 9 hash/id | chunk | sha256, chunk_id 부여 | id/hash | — |
| 10 검증 | chunk | 9장 규칙 | valid/err | 위반 수정·제외 |
| 11 출력 | chunk[] | JSONL + 통계 리포트 | 산출물 | — |

---

## 9. validation rule

**필수(위반 reject+로그):** chunk_id 전역 unique · parent_id/source_id/source_table/site_code/chunk_text 비어있지 않음 · chunk_text 10자 이상(상한 초과는 warning, 표 예외) · metadata JSON 직렬화 가능 · content_type ∈ enum · 행당 최소 1 chunk · chunk_id 형식 일치.

**빈 content 정책:** board/menu 빈본문 → skip+warning. ry 빈본문 → metadata로 `location_overview` 생성.

**HTML 정합 검증(신규):** `bd_content`(HTML) 정제 결과가 `bd_content_text`와 의미상 크게 어긋나면 warning(파싱 누락 탐지).

**통계:** 파일별 행/chunk 수, source_table·content_type별 chunk 수, 평균/최대 길이, 너무 짧은(<50)·긴(>4000) chunk 수, 표 chunk 수, skip 수, warning 목록, **HTML경로/평문경로 비율**.

---

## 10. parser 구조 (코드 미작성, 인터페이스만)

```
SourceExtractor                 # DB(PK기반) 하이브리드 추출 → 행 레코드(JSON id 범위)
HtmlLayoutParser                # 공통 HTML: 탭/섹션/표/목록 분리, table→markdown, clean
ChunkingService                 # 오케스트레이션: 추출→분기→파서→검증→출력
 ├─ BaseChunkParser (abc)       # normalize, build_chunk_text, make_chunk_id, hash
 ├─ CmsBoardChunkParser         # HtmlLayoutParser 사용, bc_id→content_type, 평문 fallback
 ├─ CmsMenuContentsChunkParser  # 탭분할(_tNN) + 표 chunk, menu_code/menu_path 메타
 ├─ RyInfoLocaChunkParser       # 위치개요 합성 + 교통/주차 분리
 └─ GenericChunkParser          # fallback
ContentTypeClassifier           # bc_id/menu_path/keyword 룰 분리 모듈
ChunkValidator                  # 9장 규칙 + 통계 리포트
```
- 라우팅: `source_table` → parser. HTML/평문은 parser 내부에서 `html_yn`/태그로 분기.
- `HtmlLayoutParser`가 v2의 핵심 신규 컴포넌트(레이아웃 청킹 엔진).

---

## 11. edge case

- **탭 분할 행**(`royal_tomb_tab`, `sub_con_tab`): 탭별로 별도 `source_id(_tNN)`. 탭 라벨 누락/중복 주의.
- **menu_code 비고유**(R106040000×3, R308020000×5): parent는 PK 기준이라 무충돌, 단 menu_code 필터 시 복수 페이지 동시 검색됨.
- **거대 HTML**(31k~39k자): 탭→섹션→표로 자연 분할되므로 길이기반 분할 불필요.
- **`bd_htmlyn` 불일치**(태그 있는데 'N', 또는 NULL): 태그 탐지로 실제 경로 결정(플래그 맹신 금지).
- **장식 마크업/인라인 style·폰트**: 제거하되 한자/alt 텍스트 보존.
- **표 셀 병합/빈 셀**: Markdown 복원 시 열 정렬 깨질 수 있음 → 실패 시 원문 보존.
- **ry 기간성 공지**(창경궁 주차 2025–2026 폐쇄): 정적 적재하되 만료 갱신 정책 필요.
- **HTML 주석 잔재**(`<!-- [S] … -->`): 제거.

---

## 12. 미해결/결정 권장

1. 임베딩 모델/차원/메트릭 (표 chunk 길이 상한에 영향).
2. 표 기본 정책: Markdown 재구성(권장) vs 원문 보존 — 복원 실패 시 자동 원문 fallback.
3. `bd_content_text`를 검증 보조로만 쓸지, HTML 파싱 불가 행의 본문으로 채택할지.
4. ry 좌표 geo 검색 도입 여부(도입 시 lat/lng scalar 승격).
5. 추후 범위 확장 시(notice01 4,399건 등) content_type 매핑표 완성 + 비정보성(qna 개인글 등) 제외 정책.

---

## 13. 부록 — 검증에 사용한 사실(재현용)

- 접속: `ROYAL_HOST=192.168.12.55:33000`, db/user=`royal` (pycubrid, **읽기 전용 SELECT만 수행**).
- JSON id → PK 매칭: board 150/150(`bd_idx`), ry 25/25(`il_idx`), menu 40/49 직접(`mc_idx`) + 9 탭분할(`_tNN`, 베이스 2행).
- board 150 = `bc_id='storyBoard'` ∧ `bd_htmlyn='Y'` (전부 HTML).
- menu `<table>` 보유 781/1,114, 탭 구조 클래스: `tab_menu`/`tab_con`/`data-tab`.
