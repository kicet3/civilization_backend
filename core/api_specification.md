# Mini Civ 게임 API 명세서

## 소개

이 문서는 Mini Civ 게임의 백엔드 API와 게임 어드바이스 시스템에 대한 기술 명세를 제공합니다.

## 1. LLM 설정

### 파일: `core/llm.py`

LLM(Large Language Model) 클라이언트의 다양한 설정을 포함합니다.

| 모델 인스턴스 | 용도 | 모델명 | 주요 특징 |
|--------------|------|-------|----------|
| `llm` | 기본 모델 | gpt-4o-mini | temperature=0.7, max_tokens=512 |
| `production_llm` | 프로덕션용 | gpt-4-turbo | temperature=0.2, max_tokens=1024 |
| `economy_llm` | 저비용 모델 | gpt-3.5-turbo | temperature=0.5, max_tokens=512 |

## 2. 프롬프트 템플릿

### 파일: `core/prompts/advice_prompt.py`

다양한 게임 전략 조언을 위한 프롬프트 템플릿을 제공합니다.

| 프롬프트 | 용도 | 입력 변수 |
|---------|------|-----------|
| `advice_prompt` | 일반 게임 어드바이스 | contexts, user_question |
| `production_advice_prompt` | 도시 생산 추천 | city_data, era, resources, policies, turns_remaining |
| `ai_production_prompt` | AI 턴용 생산 결정 | civ_name, city_data, era, resources, turns_remaining |

## 3. 도구(Tools)

### 3.1 게임 API 도구

**파일**: `core/tools/game_api.py`

게임 상태 조회 및 업데이트를 위한 HTTP API 클라이언트입니다.

#### 명령어 목록:

| 명령어 | 설명 | 필수 파라미터 | 선택 파라미터 | 반환 형식 |
|-------|------|-------------|--------------|----------|
| `get_state` | 게임 상태 조회 | game_id | - | JSON |
| `get_cities` | 도시 목록 조회 | game_id | player_id | JSON |
| `get_city` | 도시 상세 정보 | game_id, city_id | - | JSON |
| `get_production` | 생산 큐 조회 | game_id, city_id | - | JSON |
| `apply_actions` | 액션 적용 | game_id, action_data(JSON) | - | JSON |

#### 사용 예시:
```
get_state game_id=123456
get_cities game_id=123456 player_id=player1
get_city game_id=123456 city_id=city1
get_production game_id=123456 city_id=city1
apply_actions 123456 [{"type":"production","cityId":"city1","itemType":"unit","itemId":"warrior"}]
```

### 3.2 벡터 검색 도구

**파일**: `core/tools/vector_retrieval.py`

게임 공략 및 어드바이스를 위한 벡터 검색 도구입니다.

#### 데이터 카테고리:

| 카테고리 | 설명 | 데이터 예시 |
|---------|------|------------|
| units | 게임 유닛 정보 | 전사, 궁수, 개척자 등 |
| buildings | 건물 정보 | 도서관, 시장, 성벽 등 |
| technologies | 기술 정보 | 농업, 철기, 문자 등 |
| eras | 시대 정보 | 고대, 고전, 중세 등 |
| strategies | 게임 전략 | 초반 도시 확장, 과학 중심 등 |

#### 사용 예시:
```python
# 쿼리 예시
result = vector_tool._run("고대 시대에 좋은 생산 아이템 추천")
```

## 4. API 엔드포인트

이 도구들이 사용하는 백엔드 API 엔드포인트는 다음과 같습니다:

### 4.1 게임 상태 및 도시 API

| 엔드포인트 | 메소드 | 설명 | 파라미터 |
|-----------|-------|------|----------|
| `/game/state` | GET | 게임 상태 조회 | gameId |
| `/city/{gameId}/cities` | GET | 도시 목록 | player_id(선택) |
| `/city/{gameId}/city/{cityId}` | GET | 도시 상세 | - |
| `/city/{gameId}/city/{cityId}/production` | GET | 생산 큐 | - |
| `/city/{gameId}/city/{cityId}/production` | POST | 생산 아이템 추가 | gameId, cityId, itemType, itemId |

### 4.2 맵 관련 API

| 엔드포인트 | 메소드 | 설명 | 파라미터 |
|-----------|-------|------|----------|
| `/map/data` | GET | 내륙 바다(Inland Sea) 형태의 맵 데이터 반환 | - |
| `/map/adjacent` | GET | 지정된 타일 주변의 인접 타일 정보 반환 | q, r |

## 5. 데이터 모델

### 5.1 생산 추천 응답 형식

```json
[
  {
    "itemType": "unit" | "building",
    "itemId": "항목ID",
    "name": "항목 이름",
    "priority": 1-3,
    "reason": "추천 이유 (간략히)"
  }
]
```

### 5.2 AI 턴 생산 결정 응답 형식

```json
[
  {
    "itemType": "unit" | "building",
    "itemId": "항목ID",
    "priority": 1
  },
  {
    "itemType": "unit" | "building",
    "itemId": "항목ID",
    "priority": 2
  }
]
```

### 5.3 맵 데이터 모델

#### 맵 데이터 응답 형식

```json
{
  "hexagons": [
    {
      "q": 0,
      "r": 0,
      "s": 0,
      "terrain": "PLAINS",
      "resource": "WHEAT",
      "visible": true,
      "explored": true,
      "city_id": "city_id",
      "unit_id": "unit_id",
      "occupant": "Civilization Name"
    },
    // ... 더 많은 타일
  ]
}
```

#### 인접 타일 응답 형식

```json
{
  "hexagons": [
    {
      "q": 1,
      "r": 0,
      "s": -1,
      "terrain": "PLAINS",
      "resource": "WHEAT",
      "visible": true,
      "explored": true
    },
    // ... 더 많은 인접 타일 (총 6개)
  ]
}
```

## 6. 설정 방법

1. OpenAI API 키 설정:
   ```
   export OPENAI_API_KEY="your-api-key"
   ```

2. 벡터 스토어 초기화:
   - 첫 실행 시 자동으로 생성됩니다.
   - 기본 저장 경로: `./vector_data`

3. API 서버 연결:
   - 기본 URL: `http://localhost:8000`

## 7. 맵 생성 시스템

### 7.1 맵 종류

현재는 "내륙 바다(Inland Sea)" 스타일의 맵만 지원합니다. 이 맵은 중앙에 바다가 있고 그 주변으로 육지가 둘러싸인 형태입니다.

### 7.2 맵 생성 파라미터

| 파라미터 | 설명 | 기본값 |
|---------|------|-------|
| width | 맵의 가로 크기 | 21 |
| height | 맵의 세로 크기 | 19 |
| sea_radius | 내륙 바다의 반지름 | min(width, height) // 3 |

### 7.3 문명 배치

맵에는 다음과 같은 문명들이 기본적으로 배치됩니다:

| 문명 | 수도 위치 | 초기 유닛 |
|-----|----------|----------|
| Korea (플레이어) | (4, 3) | warrior-1, settler-1 |
| Japan | (16, 3) | warrior-2 |
| China | (4, 15) | warrior-3 |
| Mongolia | (16, 15) | warrior-4 |
| Russia | (10, 2) | warrior-5 |
| Rome | (10, 16) | warrior-6 |

### 7.4 지형 및 자원 시스템

맵에는 다음과 같은 지형 타입이 생성됩니다:

- **해양 지형**: OCEAN, COAST
- **육지 지형**: PLAINS, GRASSLAND, HILLS, FOREST, DESERT
- **이동 불가 지형**: MOUNTAIN

자원은 지형에 따라 다음과 같이 배치됩니다:

- **평원(PLAINS)**: WHEAT, HORSES
- **초원(GRASSLAND)**: CATTLE, SHEEP
- **언덕(HILLS)**: IRON, COAL
- **사막(DESERT)**: GOLD
- **해안(COAST)**: FISH 