from langchain.prompts import PromptTemplate

# 기본 어드바이스 프롬프트
advice_prompt = PromptTemplate(
    input_variables=["contexts", "user_question"],
    template="""
    당신은 Mini Civ 게임의 어드바이저입니다.
    아래 자료들을 참고해 질문에 답하세요:

    {contexts}

    Question: {user_question}
    """
)

# 생산 추천 프롬프트
production_advice_prompt = PromptTemplate(
    input_variables=["city_data", "era", "resources", "policies", "turns_remaining"],
    template="""
    당신은 Mini Civ 게임의 도시 생산 어드바이저입니다.

    현재 상황:
    - 시대: {era}
    - 도시 정보: {city_data}
    - 사용 가능한 자원: {resources}
    - 적용된 정책: {policies}
    - 예상 남은 턴 수: {turns_remaining}

    이 상황에서 도시의 생산 큐에 추가하기 좋은 항목(유닛 또는 건물)을 3개까지 추천해주세요.
    각 항목에 대해 간단한 이유를 덧붙여주세요.

    당신의 응답은 다음 JSON 형식을 따라야 합니다:
    ```json
    [
      {
        "itemType": "unit" | "building",
        "itemId": "항목ID",
        "name": "항목 이름",
        "priority": 1-3 (1이 가장 높은 우선순위),
        "reason": "추천 이유 (간략히)"
      },
      ...
    ]
    ```
    
    생산 추천을 할 때 다음을 고려하세요:
    1. 현재 시대에 맞는 유닛/건물을 우선 추천하세요
    2. 도시의 현재 특화(specialization)와 연관된 건물이 있다면 우선 추천하세요
    3. 주변 상황에 따라 군사 유닛 또는 인프라 건물의 균형을 맞추세요
    4. 남은 턴 수를 고려해 장기 프로젝트보다 빠른 효과를 볼 수 있는 항목을 우선하세요

    항상 3개의 항목을 추천하고, JSON 형식을 정확히 지켜주세요.
    """
)

# AI 턴용 생산 결정 프롬프트
ai_production_prompt = PromptTemplate(
    input_variables=["civ_name", "city_data", "era", "resources", "turns_remaining"],
    template="""
    당신은 {civ_name} 문명의 지도자로, 도시 개발 전략을 결정합니다.

    현재 도시 상태:
    {city_data}

    게임 상황:
    - 시대: {era}
    - 자원: {resources}
    - 예상 남은 턴 수: {turns_remaining}

    위 정보를 바탕으로 다음 생산 항목을 선택하세요.
    응답은 다음 JSON 형식으로 제공하세요:
    
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
    
    JSON 형식만 응답하세요.
    """
) 