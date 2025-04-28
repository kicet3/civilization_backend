from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import os
import json
import uuid
import datetime
from datetime import datetime
import httpx
import random
# Ollama 관련 임포트 추가
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_ollama import ChatOllama
# 메모리 관련 임포트 추가
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain.chains import ConversationChain
# Prisma 클라이언트 임포트 추가
from db.client import prisma

# API 라우터 설정
router = APIRouter(
    responses={404: {"description": "Not found"}},
)

# 모델 정의
class Message(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None

class MemoryData(BaseModel):
    """대화 메모리 데이터 모델"""
    summary: str = ""
    key_points: List[str] = []
    last_topics: List[str] = []
    sentiment: str = "neutral"  # positive, neutral, negative

class DiplomacySession(BaseModel):
    session_id: str
    civilization_id: int
    player_name: str
    messages: List[Message]
    last_interaction: str
    relationship_score: int
    remaining_interactions: int
    is_first_encounter: bool
    can_interact_again_turn: Optional[int] = None
    memory_data: Optional[MemoryData] = None  # 대화 메모리 데이터 추가

class DiplomacyRequest(BaseModel):
    game_id: int
    player_name: str
    civilization_id: int
    message: Optional[str] = None

class DiplomacyResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# 메모리 저장소 (실제 구현에서는 데이터베이스 사용을 권장)
diplomacy_sessions: Dict[str, DiplomacySession] = {}

# 문명별 메모리 저장소
civilization_memories: Dict[str, ConversationBufferMemory] = {}

# 세션 ID 생성 함수
def generate_session_id(player_name: str, civilization_id: int) -> str:
    """player_name과 civilization_id로 고유한 세션 ID를 생성합니다."""
    # 특수문자 및 공백을 제거하여 안전한 키 생성
    safe_name = "".join(c for c in player_name if c.isalnum())
    return f"dipl_{safe_name}_{civilization_id}"

# 기본 시스템 프롬프트
SYSTEM_PROMPT = """당신은 문명 게임에서 AI 문명의 외교관 역할을 맡고 있습니다.
플레이어와의 대화를 통해 관계를 형성하고, 문명의 특성과 성격에 맞게 응답해야 합니다.
문명마다 고유한 특성과 성격이 있으며, 이에 따라 대화 스타일과 태도가 달라집니다.
대화를 통해 플레이어와의 관계 점수가 결정되며, 점수에 따라 향후 외교 관계에 영향을 미칩니다.
답변은 짧고 간결하게 하되, 문명의 특성을 잘 반영해야 합니다.
이전 대화 내용을 기억하고 대화의 연속성을 유지하세요.
"""

# 문명별 프롬프트 추가 정보
CIVILIZATION_TRAITS = {
    1: {
        "name": "로마",
        "trait": "규율과 질서를 중시하며, 강력한 군사력과 행정 체계를 가진 문명입니다.",
        "personality": "권위적이고 직설적이며, 질서와 법을 중요시합니다."
    },
    2: {
        "name": "그리스",
        "trait": "학문과 예술을 중시하며, 철학과 민주주의의 발상지입니다.",
        "personality": "지적이고 사려 깊으며, 토론과 대화를 즐깁니다."
    },
    3: {
        "name": "이집트",
        "trait": "건축과 종교를 중시하며, 나일강의 혜택을 받은 고대 문명입니다.",
        "personality": "신비롭고 종교적이며, 전통을 중요시합니다."
    },
    4: {
        "name": "중국",
        "trait": "기술과 문화를 중시하며, 오랜 역사와 전통을 가진 문명입니다.",
        "personality": "현명하고 인내심이 강하며, harmony와 균형을 추구합니다."
    },
    5: {
        "name": "몽골",
        "trait": "기마와 정복을 중시하며, 넓은 영토를 지배했던 문명입니다.",
        "personality": "직설적이고 호전적이며, 강함과 자유를 중요시합니다."
    },
    6: {
        "name": "아즈텍",
        "trait": "희생과 전쟁을 중시하며, 독특한 문화와 종교를 가진 문명입니다.",
        "personality": "격렬하고 신비로우며, 종교 의식과 희생을 중요시합니다."
    }
}

# 문명 정보를 데이터베이스에서 가져오는 함수
async def get_civilization_info(civilization_id: int) -> Dict[str, Any]:
    """데이터베이스에서 문명 정보를 가져옵니다."""
    try:
        # 먼저 게임 내 문명 정보 조회 (GameCiv 테이블)
        civ = await prisma.gameciv.find_first(
            where={
                "civTypeId": civilization_id
            },
            include={
                "civType": True  # CivType 관련 정보 포함
            }
        )
        
        if civ:
            # 문명 정보가 있는 경우
            civ_type = civ.civType if hasattr(civ, 'civType') and civ.civType else None
            
            # 문명 유형 정보가 있으면 해당 정보 활용, 없으면 기본 정보 사용
            if civ_type:
                personality = get_personality_by_traits(civ_type.name, civ_type.leaderName)
                trait = get_trait_description(civ_type.name)
                
                return {
                    "id": civilization_id,
                    "name": civ_type.name,
                    "leader": civ_type.leaderName,
                    "trait": trait,
                    "personality": personality,
                    "color": civ.color if hasattr(civ, 'color') else "blue"
                }
            else:
                # CivType 정보가 없지만 civTypeId는 있는 경우 CivType 직접 조회
                if hasattr(civ, 'civTypeId'):
                    civ_type = await prisma.civtype.find_unique(
                        where={"id": civ.civTypeId}
                    )
                    
                    if civ_type:
                        personality = get_personality_by_traits(civ_type.name, civ_type.leaderName)
                        trait = get_trait_description(civ_type.name)
                        
                        return {
                            "id": civilization_id,
                            "name": civ_type.name,
                            "leader": civ_type.leaderName,
                            "trait": trait,
                            "personality": personality,
                            "color": civ.color if hasattr(civ, 'color') else "blue"
                        }
                
                # 문명 유형 정보가 없는 경우 기본 정보
                return {
                    "id": civilization_id,
                    "name": civ.name if hasattr(civ, 'name') else f"{CIVILIZATION_TRAITS.get(civilization_id, {}).get('name', '알 수 없는 문명')}",
                    "leader": "알 수 없는 지도자",
                    "trait": "특별한 특성이 없습니다.",
                    "personality": "중립적",
                    "color": civ.color if hasattr(civ, 'color') else "blue"
                }
        
        # 게임 내 문명이 없으면 CivType 테이블 직접 조회
        civ_type = await prisma.civtype.find_first(
            where={
                "id": civilization_id
            }
        )
        
        if civ_type:
            personality = get_personality_by_traits(civ_type.name, civ_type.leaderName)
            trait = get_trait_description(civ_type.name)
            
            return {
                "id": civilization_id,
                "name": civ_type.name,
                "leader": civ_type.leaderName,
                "trait": trait,
                "personality": personality,
                "color": "blue"
            }
            
        # 데이터베이스에 정보가 없는 경우 하드코딩된 CIVILIZATION_TRAITS 사용
        if civilization_id in CIVILIZATION_TRAITS:
            civ_data = CIVILIZATION_TRAITS[civilization_id]
            return {
                "id": civilization_id,
                "name": civ_data.get("name", f"문명 {civilization_id}"),
                "leader": civ_data.get("leaderName", "알 수 없는 지도자"),
                "trait": civ_data.get("trait", "특별한 특성이 없습니다."),
                "personality": civ_data.get("personality", "중립적"),
                "color": "blue"
            }
            
        # 모든 조회가 실패한 경우 기본값 반환
        return {
            "id": civilization_id,
            "name": f"{CIVILIZATION_TRAITS.get(civilization_id, {}).get('name', '알 수 없는 문명')}",
            "leader": "알 수 없는 지도자",
            "trait": "특별한 특성이 없습니다.",
            "personality": "중립적",
            "color": "blue"
        }
        
    except Exception as e:
        print(f"문명 정보 조회 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 오류 발생 시 기본값 반환
        return {
            "id": civilization_id,
            "name": f"{CIVILIZATION_TRAITS.get(civilization_id, {}).get('name', '알 수 없는 문명')}",
            "leader": "알 수 없는 지도자",
            "trait": "특별한 특성이 없습니다.",
            "personality": "중립적",
            "color": "blue"
        }

# 문명 이름과 지도자 이름을 기반으로 성격 결정
def get_personality_by_traits(civ_name: str, leader_name: str) -> str:
    """문명 이름과 지도자 이름을 기반으로 성격을 결정합니다."""
    # 문명 이름 기반 성격 결정
    if "로마" in civ_name:
        return "권위적이고 직설적이며, 질서와 법을 중요시합니다."
    elif "그리스" in civ_name:
        return "지적이고 사려 깊으며, 토론과 대화를 즐깁니다."
    elif "이집트" in civ_name:
        return "신비롭고 종교적이며, 전통을 중요시합니다."
    elif "중국" in civ_name:
        return "현명하고 인내심이 강하며, harmony와 균형을 추구합니다."
    elif "몽골" in civ_name:
        return "직설적이고 호전적이며, 강함과 자유를 중요시합니다."
    elif "아즈텍" in civ_name:
        return "격렬하고 신비로우며, 종교 의식과 희생을 중요시합니다."
    
    # 지도자 이름 기반 성격 결정
    if "세종" in leader_name:
        return "지혜롭고 개방적이며, 과학과 문화를 중시합니다."
    elif "간디" in leader_name:
        return "평화롭고 인내심이 강하며, 비폭력과, 정신적 가치를 중시합니다."
    elif "처칠" in leader_name:
        return "단호하고 용감하며, 전략적 사고와 애국심이 강합니다."
    elif "알렉산더" in leader_name or "알렉산드로스" in leader_name:
        return "정복욕이 강하고 야심차며, 모험과 도전을 즐깁니다."
    elif "클레오파트라" in leader_name:
        return "매혹적이고 전략적이며, 외교와 무역을 중요시합니다."
    elif "칭기스" in leader_name:
        return "정복자로서 호전적이고 용맹하며, 충성과 규율을 중요시합니다."
    
    # 기본 성격
    return "외교적이고 전략적이며, 자국의 이익을 우선시합니다."

# 문명 이름에 따른 특성 설명 생성
def get_trait_description(civ_name: str) -> str:
    """문명 이름에 따른 특성 설명을 생성합니다."""
    if "로마" in civ_name:
        return "규율과 질서를 중시하며, 강력한 군사력과 행정 체계를 가진 문명입니다."
    elif "그리스" in civ_name:
        return "학문과 예술을 중시하며, 철학과 민주주의의 발상지입니다."
    elif "이집트" in civ_name:
        return "건축과 종교를 중시하며, 나일강의 혜택을 받은 고대 문명입니다."
    elif "중국" in civ_name:
        return "기술과 문화를 중시하며, 오랜 역사와 전통을 가진 문명입니다."
    elif "몽골" in civ_name:
        return "기마와 정복을 중시하며, 넓은 영토를 지배했던 문명입니다."
    elif "아즈텍" in civ_name:
        return "희생과 전쟁을 중시하며, 독특한 문화와 종교를 가진 문명입니다."
    elif "한국" in civ_name:
        return "과학과 혁신을 중시하며, 전통과 현대화의 조화를 이룬 문명입니다."
    elif "일본" in civ_name:
        return "명예와 전통을 중시하며, 군사력과 문화적 정체성이 강한 문명입니다."
    elif "러시아" in civ_name:
        return "광활한 영토와 풍부한 자원을 가진 문명으로, 추운 기후에 잘 적응했습니다."
    
    # 기본 특성
    return "독특한 문화와 전통을 가진 문명입니다."

# 문명 메모리 관리 함수
def get_civilization_memory(session_id: str, civilization_id: int) -> ConversationBufferMemory:
    """문명별 대화 메모리를 가져오거나 생성하는 함수"""
    if session_id not in civilization_memories:
        # 새 메모리 생성
        memory = ConversationBufferMemory(return_messages=True)
        civilization_memories[session_id] = memory
    
    return civilization_memories[session_id]

# 대화 메모리 요약 함수
def summarize_conversation(messages: List[Message], civ_info: Dict) -> MemoryData:
    """대화 내용을 분석하여 요약 정보를 생성하는 함수"""
    if not messages:
        return MemoryData()
    
    # 간단한 요약 생성
    last_messages = messages[-min(10, len(messages)):]
    summary = f"{civ_info['name']} 문명과의 최근 대화"
    
    # 주요 키워드 추출
    keywords = ["평화", "전쟁", "무역", "동맹", "기술", "문화", "자원", "협력"]
    key_points = []
    
    # 감정 분석
    positive_words = ["감사", "좋음", "동의", "협력", "동맹", "평화", "존중", "우정"]
    negative_words = ["분노", "불만", "전쟁", "공격", "적대", "위협", "파괴"]
    
    positive_count = 0
    negative_count = 0
    topics = set()
    
    for msg in last_messages:
        content = msg.content.lower()
        
        # 키워드 확인
        for keyword in keywords:
            if keyword in content and keyword not in topics:
                topics.add(keyword)
                key_points.append(f"{keyword}에 관한 논의가 있었습니다.")
        
        # 감정 분석
        for word in positive_words:
            if word in content:
                positive_count += 1
        
        for word in negative_words:
            if word in content:
                negative_count += 1
    
    # 감정 상태 결정
    sentiment = "neutral"
    if positive_count > negative_count + 2:
        sentiment = "positive"
    elif negative_count > positive_count + 1:
        sentiment = "negative"
    
    return MemoryData(
        summary=summary,
        key_points=key_points[:5],  # 최대 5개 주요 포인트
        last_topics=list(topics)[:3],  # 최대 3개 주제
        sentiment=sentiment
    )

# 관계 점수 계산 함수 개선
def calculate_relationship_score(messages: List[Message], current_score: int, memory_data: MemoryData) -> int:
    """대화 내용과 메모리 데이터를 기반으로 관계 점수를 계산하는 함수"""
    # 기본 점수는 현재 점수 유지
    score = current_score
    
    # 최근 메시지만 분석 (최대 5개)
    recent_messages = messages[-min(5, len(messages)):]
    user_messages = [msg for msg in recent_messages if msg.role == "user"]
    
    # 긍정적/부정적 키워드에 따른 점수 조정
    positive_keywords = ["동맹", "친구", "협력", "평화", "무역", "도움", "지원", "감사", "존중", "공정", "제안", "발전"]
    negative_keywords = ["전쟁", "공격", "위협", "적", "파괴", "침략", "배신", "거부", "무시", "분노", "파괴", "제재"]
    
    # 최근 메시지 분석
    for msg in user_messages:
        content = msg.content.lower()
        
        # 긍정적 키워드 확인
        for keyword in positive_keywords:
            if keyword in content:
                score += random.randint(1, 3)  # 보다 작은 증가폭
        
        # 부정적 키워드 확인
        for keyword in negative_keywords:
            if keyword in content:
                score -= random.randint(1, 2)  # 보다 작은 감소폭
    
    # 메모리 데이터의 감정 상태 반영
    if memory_data:
        if memory_data.sentiment == "positive":
            score += 2
        elif memory_data.sentiment == "negative":
            score -= 2
        
        # 주제의 일관성 반영
        if len(memory_data.last_topics) > 0:
            score += 1  # 대화 주제가 있으면 약간 증가
    
    # 점수 범위 제한 (0-100)
    score = max(0, min(score, 100))
    
    return score

# LLM 응답 생성 함수
async def generate_llm_response(session_id: str, messages: List[Message], civilization_id: int) -> str:
    """환경에 따라 Gemini 또는 Ollama를 통해 응답을 생성하는 함수"""
    
    # 문명 정보 추가
    civ_info = await get_civilization_info(civilization_id)
    
    # 메모리 가져오기
    memory = get_civilization_memory(session_id, civilization_id)
    
    # 세션에서 메모리 데이터 가져오기
    session = diplomacy_sessions.get(session_id)
    memory_data = None
    if session and session.memory_data:
        memory_data = session.memory_data
    else:
        memory_data = MemoryData()
    
    # 시스템 프롬프트 조정 (메모리 정보 포함)
    system_prompt = f"{SYSTEM_PROMPT}\n\n당신은 {civ_info['name']} 문명의 외교관입니다.\n{civ_info['trait']}\n성격: {civ_info['personality']}"
    
    # 메모리 정보 추가
    if memory_data and memory_data.key_points:
        memory_context = "\n\n이전 대화에서 중요한 점:\n" + "\n".join(memory_data.key_points)
        system_prompt += memory_context
    
    if memory_data and memory_data.sentiment != "neutral":
        sentiment_text = "긍정적" if memory_data.sentiment == "positive" else "부정적"
        system_prompt += f"\n\n현재 대화 분위기는 {sentiment_text}입니다."
    
    try:
        # 환경 변수에 따라 다른 LLM 사용
        environment = os.getenv("ENVIRONMENT", "development")
        
        if environment == "development":
            # 개발 환경에서는 Gemini 사용
            print(f"개발 환경: Gemini 사용하여 {civ_info['name']} 문명 응답 생성")
            
            # 대화 메시지 준비
            conversation_history = []
            
            # 이전 대화에서 중요한 맥락 추가
            if len(messages) > 5:
                conversation_history.append(f"이전 대화의 요약: {memory_data.summary if memory_data.summary else '이전에 기본적인 외교 대화를 나눴습니다.'}")
                conversation_history.append("알겠습니다. 이전 대화를 기억하며 계속하겠습니다.")
            
            # 대화 메시지 추가 (최근 5개만)
            recent_messages = messages[-min(5, len(messages)):]
            for msg in recent_messages:
                if msg.role == "user":
                    conversation_history.append(f"플레이어: {msg.content}")
                    # 메모리에 사용자 메시지 저장
                    if memory:
                        memory.chat_memory.add_user_message(msg.content)
                elif msg.role == "assistant":
                    conversation_history.append(f"{civ_info['name']} 문명: {msg.content}")
                    # 메모리에 AI 메시지 저장
                    if memory:
                        memory.chat_memory.add_ai_message(msg.content)
            
            # Gemini API 호출 설정
            google_api_key = os.getenv("GOOGLE_API_KEY", "YOUR_GEMINI_API_KEY")
            gemini_model = os.getenv("GEMINI_MODEL", "gemini-pro")
            gemini_api_url = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models")
            
            # URL 구성
            # URL 끝에 슬래시가 있는지 확인하고 없으면 추가
            if not gemini_api_url.endswith('/'):
                gemini_api_url += '/'
                
            full_url = f"{gemini_api_url}{gemini_model}:generateContent"
            print(f"Gemini API 호출 URL: {full_url}")
            
            # 요청 데이터 구성
            prompt = f"{system_prompt}\n\n{''.join(conversation_history)}\n\n{civ_info['name']} 문명:"
            request_data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.8,
                    "maxOutputTokens": 500
                }
            }
            
            # Gemini API 호출
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{full_url}?key={google_api_key}",
                        json=request_data,
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        try:
                            response_text = result["candidates"][0]["content"]["parts"][0]["text"]
                            
                            # 결과가 없거나 빈 문자열인 경우 처리
                            if not response_text or response_text.strip() == "":
                                print("Gemini 응답이 비어있습니다.")
                                # 기본 응답 사용
                                response_text = f"{civ_info['name']} 문명이 당신을 환영합니다. 우리는 평화로운 관계를 희망합니다."
                            
                            # 메모리에 응답 저장
                            if memory:
                                memory.chat_memory.add_ai_message(response_text)
                                
                            return response_text
                        except (KeyError, IndexError) as e:
                            print(f"Gemini 응답 파싱 오류: {str(e)}")
                            print(f"응답: {result}")
                            # 오류 발생 시 기본 응답 사용
                            return f"{civ_info['name']} 문명이 당신을 환영합니다. 우리의 외교관이 곧 응답할 것입니다."
                    else:
                        print(f"Gemini API 오류: {response.status_code} - {response.text}")
                        # API 오류 시 기본 응답 사용
                        return f"{civ_info['name']} 문명에서 메시지를 전하려 했으나 전달이 지연되고 있습니다."
                    
            except Exception as e:
                print(f"Gemini API 호출 오류: {str(e)}")
                # Gemini 호출 오류 시 기본 응답 사용
                return f"{civ_info['name']} 문명이 당신의 제안에 관심을 보입니다. 잠시 후 다시 시도해 주세요."
        
        else:
            # 프로덕션 환경에서는 Ollama 사용
            print(f"프로덕션 환경: Ollama 사용하여 {civ_info['name']} 문명 응답 생성")
            
            # Ollama 설정
            ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
            ollama_model = os.getenv("OLLAMA_MODEL", "eeve-korean-10.8b")
            
            # LangChain 메시지 리스트 생성
            langchain_messages = [SystemMessage(content=system_prompt)]
            
            # 이전 대화에서 중요한 맥락 최대 5개 메시지 추가
            if len(messages) > 5:
                langchain_messages.append(HumanMessage(content=f"이전 대화의 요약: {memory_data.summary if memory_data.summary else '이전에 기본적인 외교 대화를 나눴습니다.'}"))
                langchain_messages.append(AIMessage(content="알겠습니다. 이전 대화를 기억하며 계속하겠습니다."))
            
            # 대화 메시지 추가 (최근 5개만)
            recent_messages = messages[-min(5, len(messages)):]
            for msg in recent_messages:
                if msg.role == "user":
                    langchain_messages.append(HumanMessage(content=msg.content))
                    # 메모리에 사용자 메시지 저장
                    if memory:
                        memory.chat_memory.add_user_message(msg.content)
                elif msg.role == "assistant":
                    langchain_messages.append(AIMessage(content=msg.content))
                    # 메모리에 AI 메시지 저장
                    if memory:
                        memory.chat_memory.add_ai_message(msg.content)
            
            # Ollama 호출
            try:
                # 외교 대화에서는 Ollama 사용
                print(f"외교 대화를 위해 Ollama 모델({ollama_model}) 사용")
                chat_model = ChatOllama(
                    model=ollama_model,
                    base_url=ollama_url,
                    temperature=0.7,
                    top_p=0.8,
                    top_k=40,
                    num_predict=500,
                )
                
                # LLM 호출
                response = chat_model.invoke(langchain_messages)
                
                # 응답 텍스트 추출
                response_text = response.content
                
                if not response_text:
                    print("Ollama 응답에 텍스트가 없습니다.")
                    return f"{civ_info['name']} 문명이 당신을 환영합니다. 우리는 평화로운 관계를 희망합니다."
                    
                # 메모리에 응답 저장
                if memory:
                    memory.chat_memory.add_ai_message(response_text)
                    
                return response_text
                
            except Exception as e:
                print(f"Ollama 호출 오류: {str(e)}")
                # Ollama 호출 오류 시 기본 응답 사용
                return f"{civ_info['name']} 문명이 당신의 제안에 관심을 보입니다. 잠시 후 다시 시도해 주세요."
                        
    except Exception as e:
        print(f"LLM 응답 생성 오류: {str(e)}")
        return f"{civ_info['name']} 문명이 응답하지 않습니다. 전송 중 오류가 발생했습니다."

# 웹소켓 연결 관리를 위한 클래스
class DiplomacyConnectionManager:
    def __init__(self):
        # 연결 관리 (session_id → WebSocket)
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            
    async def send_message(self, session_id: str, message: Dict[str, Any]):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

# 싱글톤 연결 관리자
ws_manager = DiplomacyConnectionManager()

# WebSocket을 통한 외교 대화 엔드포인트
@router.websocket("/ws/{player_name}/{civilization_id}")
async def diplomacy_ws(
    websocket: WebSocket, 
    player_name: str, 
    civilization_id: int
):
    """WebSocket을 통한 외교 대화"""
    # 세션 ID 생성
    session_id = generate_session_id(player_name, int(civilization_id))
    
    # 연결 수락
    await ws_manager.connect(websocket, session_id)
    
    try:
        # 문명 정보를 데이터베이스에서 가져오기
        civ_id = int(civilization_id)
        civ_info = await get_civilization_info(civ_id)
        
        # 세션 존재 확인 및 가져오기 또는 생성
        if session_id not in diplomacy_sessions:
            # 새 세션 생성
            print(f"{player_name}과 {civ_info['name']} 문명({civ_info['leader']}) 사이의 새로운 외교 세션 생성")
            
            new_session = DiplomacySession(
                session_id=session_id,
                civilization_id=civ_id,
                player_name=player_name,
                messages=[],
                last_interaction=datetime.now().isoformat(),
                relationship_score=30,  # 초기 점수를 30으로 설정
                remaining_interactions=10,  # 첫 조우 시 10번의 대화 기회
                is_first_encounter=True,
                memory_data=MemoryData()  # 빈 메모리 데이터 초기화
            )
            
            # 문명 특성에 따른 초기 메시지 생성
            initial_message = get_initial_message_by_traits(civ_info)
            
            # 세션 저장
            diplomacy_sessions[session_id] = new_session
            
            # 메모리 초기화
            get_civilization_memory(session_id, civ_id)
            
            # 초기 메시지 전송
            await ws_manager.send_message(session_id, {
                "type": "initial",
                "civilization_id": civ_id,
                "civilization_name": civ_info["name"],
                "civilization_trait": civ_info["trait"],
                "civilization_personality": civ_info["personality"],
                "leader_name": civ_info["leader"],
                "message": initial_message,
                "remaining_interactions": 10,
                "relationship_score": 30
            })
        else:
            # 기존 세션 가져오기
            session = diplomacy_sessions[session_id]
            print(f"{player_name}과 {civ_info['name']} 문명({civ_info['leader']}) 사이의 기존 외교 세션 로드")
            
            # 대화 가능 여부 확인
            if session.remaining_interactions <= 0:
                await ws_manager.send_message(session_id, {
                    "type": "error",
                    "message": f"{civ_info['name']} 문명과 더 이상 대화할 수 없습니다. {session.can_interact_again_turn}턴 이후에 다시 시도하세요.",
                    "can_interact_again_turn": session.can_interact_again_turn
                })
                return
            
            # 세션 상태 메시지 전송
            await ws_manager.send_message(session_id, {
                "type": "session_info",
                "civilization_id": civ_id,
                "civilization_name": civ_info["name"],
                "civilization_trait": civ_info["trait"],
                "civilization_personality": civ_info["personality"],
                "leader_name": civ_info["leader"],
                "relationship_score": session.relationship_score,
                "remaining_interactions": session.remaining_interactions,
                "previous_messages": [
                    {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
                    for msg in session.messages[-6:]  # 최근 6개 메시지만 반환
                ],
                "memory_data": {
                    "summary": session.memory_data.summary if session.memory_data else "",
                    "key_points": session.memory_data.key_points if session.memory_data else [],
                    "last_topics": session.memory_data.last_topics if session.memory_data else [],
                    "sentiment": session.memory_data.sentiment if session.memory_data else "neutral"
                }
            })
        
        # 메시지 수신 및 처리 루프
        while True:
            # 클라이언트 메시지 수신
            data = await websocket.receive_json()
            
            # 현재 세션 정보 가져오기
            session = diplomacy_sessions[session_id]
            
            # 대화 가능 여부 확인
            if session.remaining_interactions <= 0:
                await ws_manager.send_message(session_id, {
                    "type": "error",
                    "message": f"{civ_info['name']} 문명과 더 이상 대화할 수 없습니다. {session.can_interact_again_turn}턴 이후에 다시 시도하세요.",
                    "can_interact_again_turn": session.can_interact_again_turn
                })
                continue
            
            # 메시지 처리
            if data.get("type") == "message":
                user_message = data.get("content", "")
                
                if not user_message.strip():
                    await ws_manager.send_message(session_id, {
                        "type": "error",
                        "message": "빈 메시지는 보낼 수 없습니다."
                    })
                    continue
                
                # 사용자 메시지 추가
                timestamp = datetime.now().isoformat()
                user_message_obj = Message(role="user", content=user_message, timestamp=timestamp)
                session.messages.append(user_message_obj)
                
                # LLM을 사용하여 응답 생성 (문명 특성 추가 전달)
                response_content = await generate_llm_response(session_id, session.messages, civ_id)
                
                # 문명 특성에 따른 응답 조정
                response_content = adjust_response_by_traits(response_content, civ_info)
                
                # 응답 메시지 추가
                ai_message = Message(role="assistant", content=response_content, timestamp=datetime.now().isoformat())
                session.messages.append(ai_message)
                
                # 대화 메모리 업데이트
                session.memory_data = summarize_conversation(session.messages, civ_info)
                
                # 관계 점수 계산 및 업데이트
                old_score = session.relationship_score
                session.relationship_score = calculate_relationship_score(
                    session.messages, 
                    session.relationship_score, 
                    session.memory_data
                )
                score_increase = session.relationship_score - old_score
                
                # 세션 업데이트
                session.last_interaction = datetime.now().isoformat()
                session.remaining_interactions -= 1
                
                # 점수 상한 제한 (100점 이하)
                session.relationship_score = min(session.relationship_score, 100)
                
                # 마지막 대화인 경우 다음 대화 가능 턴 설정
                if session.remaining_interactions == 0:
                    # 다음 대화 가능 턴 설정 (예: 5턴 후)
                    session.can_interact_again_turn = data.get("game_id", 0) + 5
                
                # 세션 저장
                diplomacy_sessions[session_id] = session
                
                # 사용자 메시지 개수 파악 (role이 user인 메시지 개수)
                user_message_count = sum(1 for msg in session.messages if msg.role == "user")
                
                # 응답 메시지 전송 (3번째 메시지부터는 항상 관계 점수 포함)
                response_data = {
                    "type": "response",
                    "message": ai_message.content,
                    "civilization_id": civ_id,
                    "civilization_name": civ_info["name"],
                    "remaining_interactions": session.remaining_interactions,
                    "timestamp": ai_message.timestamp
                }
                
                # 3번째 메시지 이후부터는 관계 점수 정보 포함
                if user_message_count >= 3:
                    response_data.update({
                        "relationship_score": session.relationship_score,
                        "score_change": score_increase,
                        "memory_summary": session.memory_data.summary if session.memory_data else "",
                        "sentiment": session.memory_data.sentiment if session.memory_data else "neutral"
                    })
                
                await ws_manager.send_message(session_id, response_data)
            
            # 턴 진행 알림 처리
            elif data.get("type") == "turn_update":
                game_id = data.get("game_id", 0)
                
                # 대화 가능 여부 확인 및 업데이트
                if session.can_interact_again_turn is not None and game_id >= session.can_interact_again_turn:
                    # 대화 가능 상태로 업데이트
                    session.remaining_interactions = 5  # 재개 시 5번의 대화 기회
                    session.can_interact_again_turn = None
                    
                    # 메모리에 재개 정보 추가
                    if session.memory_data:
                        if "재개" not in session.memory_data.key_points:
                            session.memory_data.key_points.append("외교 관계가 재개되었습니다.")
                            if len(session.memory_data.key_points) > 5:
                                session.memory_data.key_points = session.memory_data.key_points[-5:]
                    
                    # 세션 저장
                    diplomacy_sessions[session_id] = session
                    
                    # 문명 특성에 따른 재개 메시지 생성
                    resume_message = get_resume_message_by_traits(civ_info)
                    
                    # 대화 재개 알림
                    await ws_manager.send_message(session_id, {
                        "type": "diplomacy_resumed",
                        "message": resume_message,
                        "civilization_id": civ_id,
                        "civilization_name": civ_info["name"],
                        "remaining_interactions": session.remaining_interactions,
                        "relationship_score": session.relationship_score
                    })
    
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id)
        print(f"WebSocket 연결 종료: {session_id}")
    except Exception as e:
        import traceback
        print(f"WebSocket 외교 오류: {str(e)}")
        print(traceback.format_exc())
        
        # 에러 메시지 전송 시도
        try:
            await ws_manager.send_message(session_id, {
                "type": "error",
                "message": f"오류 발생: {str(e)}"
            })
        except:
            pass
        
        ws_manager.disconnect(session_id)

# 문명 특성에 따른 초기 메시지 생성 함수
def get_initial_message_by_traits(civ_info: Dict[str, str]) -> str:
    """문명 특성에 따른 초기 메시지 생성"""
    civ_name = civ_info.get("name", "알 수 없는 문명")
    leader_name = civ_info.get("leader", "알 수 없는 지도자")
    personality = civ_info.get("personality", "").lower()
    trait = civ_info.get("trait", "").lower()
    
    # 지도자 이름을 포함한 메시지로 개선
    
    # 성격에 따른 메시지 차별화
    if "권위" in personality or "직설적" in personality:
        return f"{civ_name}의 지도자 {leader_name}이(가) 당신을 만났습니다. 우리는 강력한 질서와 규율을 중시합니다. 당신의 의도가 무엇인지 명확히 밝히십시오."
    
    elif "지적" in personality or "사려 깊" in personality or "토론" in personality:
        return f"{civ_name}의 지도자 {leader_name}이(가) 당신을 환영합니다. 당신과 지식과 지혜를 나누는 대화를 나누길 기대합니다. 어떤 논의를 원하시나요?"
    
    elif "신비" in personality or "종교적" in personality or "전통" in personality:
        return f"{civ_name}의 통치자 {leader_name}이(가) 당신에게 고대 지혜와 전통을 보여드립니다. 우리의 오랜 역사를 존중해주시기 바랍니다. 어떤 목적으로 찾아오셨습니까?"
    
    elif "현명" in personality or "인내" in personality or "균형" in personality:
        return f"{civ_name}의 지도자 {leader_name}은(는) 조화와 균형을 추구합니다. 상호 이익이 되는 관계를 맺기를 희망합니다. 어떤 제안을 가지고 오셨습니까?"
    
    elif "호전적" in personality or "강함" in personality or "정복" in trait:
        return f"{civ_name}의 정복자 {leader_name}이(가) 당신을 주시합니다. 우리는 강력한 군사력과 용맹함으로 알려져 있습니다. 당신의 문명은 동맹이 될까요, 아니면 정복 대상이 될까요?"
    
    elif "격렬" in personality or "희생" in trait:
        return f"{civ_name}의 통치자 {leader_name}이(가) 의식에 당신을 초대합니다. 우리의 신들은 당신의 방문을 주시하고 있습니다. 어떤 목적으로 우리 땅에 발을 들였습니까?"
    
    # 기본 메시지
    return f"{civ_name}의 지도자 {leader_name}이(가) 당신과의 대화를 요청했습니다. 어떤 논의를 원하십니까?"
    
# 문명 특성에 따른 대화 재개 메시지 생성 함수
def get_resume_message_by_traits(civ_info: Dict[str, str]) -> str:
    """문명 특성에 따른 대화 재개 메시지 생성"""
    civ_name = civ_info.get("name", "알 수 없는 문명")
    leader_name = civ_info.get("leader", "알 수 없는 지도자")
    personality = civ_info.get("personality", "").lower()
    trait = civ_info.get("trait", "").lower()
    
    # 지도자 이름을 포함한 메시지로 개선
    
    # 성격에 따른 메시지 차별화
    if "권위" in personality or "직설적" in personality:
        return f"{civ_name}의 지도자 {leader_name}이(가) 다시 당신을 만날 시간을 마련했습니다. 우리의 논의를 계속합시다."
    
    elif "지적" in personality or "사려 깊" in personality:
        return f"{civ_name}의 지도자 {leader_name}은(는) 당신과의 대화를 재개하기를 원합니다. 이전 논의에서 얻은 통찰력을 바탕으로 대화를 이어갑시다."
    
    elif "신비" in personality or "종교적" in personality:
        return f"{civ_name}의 통치자 {leader_name}이(가) 당신과의 대화를 재개하도록 허락했습니다. 우리의 성스러운 논의를 계속합시다."
    
    elif "현명" in personality or "인내" in personality:
        return f"{civ_name}의 지도자 {leader_name}은(는) 균형과 조화의 정신으로 당신과의 외교를 재개합니다. 서로에게 유익한 대화가 되길 바랍니다."
    
    elif "호전적" in personality or "강함" in personality:
        return f"{civ_name}의 지도자 {leader_name}이(가) 당신을 다시 불렀습니다. 이전 논의의 결과가 만족스럽지 않았습니다. 더 나은 제안을 기대합니다."
    
    elif "격렬" in personality or "희생" in trait:
        return f"{civ_name}의 통치자 {leader_name}의 제사장들이 당신과의 대화를 재개할 시간이 왔음을 알립니다. 신들이 우리의 대화를 지켜보고 있습니다."
    
    # 기본 메시지
    return f"{civ_name}의 지도자 {leader_name}이(가) 외교 관계를 재개하기로 결정했습니다."

# 문명 특성에 따른 응답 조정 함수
def adjust_response_by_traits(response: str, civ_info: Dict[str, str]) -> str:
    """문명 특성에 따라 응답을 조정하는 함수"""
    # 응답이 비어있는 경우 처리
    if not response or len(response.strip()) == 0:
        return get_initial_message_by_traits(civ_info)
    
    civ_name = civ_info.get("name", "알 수 없는 문명")
    leader_name = civ_info.get("leader", "알 수 없는 지도자")
    personality = civ_info.get("personality", "").lower()
    
    # 이미 충분히 특성이 반영된 응답인 경우 그대로 반환
    if civ_name in response and leader_name in response:
        return response
    
    # 성격에 따른 응답 스타일 조정
    prefix = ""
    suffix = ""
    
    if "권위" in personality or "직설" in personality:
        prefix = f"{civ_name}의 지도자 {leader_name}은(는) "
        suffix = " 우리의 결정은 흔들림이 없을 것입니다."
    
    elif "지적" in personality or "사려 깊" in personality:
        prefix = f"{civ_name}의 지도자 {leader_name}은(는) "
        suffix = " 지식과 지혜가 우리의 안내자입니다."
    
    elif "신비" in personality or "종교" in personality:
        prefix = f"{civ_name}의 지도자 {leader_name}은(는) "
        suffix = " 신들의 뜻을 따르는 것이 현명할 것입니다."
    
    elif "현명" in personality or "균형" in personality:
        prefix = f"{civ_name}의 지도자 {leader_name}은(는) "
        suffix = " 조화와 균형 속에서 최선의 결정을 내리겠습니다."
    
    elif "호전" in personality or "강함" in personality:
        prefix = f"{civ_name}의 지도자 {leader_name}은(는) "
        suffix = " 약함은 용납되지 않습니다."
    
    elif "격렬" in personality or "희생" in personality:
        prefix = f"{civ_name}의 지도자 {leader_name}은(는) "
        suffix = " 신들은 희생을 요구합니다."
    
    # 응답이 너무 짧은 경우에만 접두사/접미사 추가
    if len(response) < 100 and not response.startswith(f"{civ_name}") and not response.startswith(f"{leader_name}"):
        # 첫 글자를 소문자로 변경하여 접두사와 자연스럽게 연결
        if response[0].isupper() and len(response) > 1:
            response = response[0].lower() + response[1:]
            
        # 접두사가 비어있지 않고 응답이 접두사로 시작하지 않는 경우
        if prefix and not response.startswith(prefix):
            response = prefix + response
            
        # 접미사가 비어있지 않고 응답이 접미사로 끝나지 않는 경우
        if suffix and not response.endswith(suffix):
            # 마침표로 끝나는 경우 마침표 제거
            if response.endswith("."):
                response = response[:-1]
            response = response + suffix
    
    return response

# 추가: 관계 점수 조회 API 간소화 (기존 API에 추가로)
@router.get("/relationship/{player_name}/{civilization_id}")
async def get_simple_relationship(player_name: str, civilization_id: int):
    """문명과의 관계 점수를 간단하게 조회합니다."""
    try:
        session_id = generate_session_id(player_name, civilization_id)
        
        # 세션 존재 확인
        if session_id not in diplomacy_sessions:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "외교 세션이 없습니다."}
            )
        
        session = diplomacy_sessions[session_id]
        civ_info = await get_civilization_info(civilization_id)
        
        return {
            "success": True,
            "civilization_name": civ_info["name"],
            "relationship_score": session.relationship_score,
            "remaining_interactions": session.remaining_interactions,
            "can_interact": session.remaining_interactions > 0,
            "can_interact_again_turn": session.can_interact_again_turn
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"오류 발생: {str(e)}"
        }

# 첫 번째 조우 처리 API
@router.post("/first-encounter", response_model=DiplomacyResponse)
async def first_encounter(request: DiplomacyRequest):
    """플레이어가 새로운 문명을 처음 조우했을 때의 처리"""
    try:
        player_name = request.player_name
        civilization_id = request.civilization_id
        session_id = generate_session_id(player_name, civilization_id)
        
        # 이미 조우한 문명인지 확인
        if session_id in diplomacy_sessions:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "이미 조우한 문명입니다.", "data": None}
            )
        
        # 새 세션 생성
        new_session = DiplomacySession(
            session_id=session_id,
            civilization_id=civilization_id,
            player_name=player_name,
            messages=[],
            last_interaction=datetime.now().isoformat(),
            relationship_score=30,  # 초기 점수를 30으로 설정
            remaining_interactions=10,  # 첫 조우 시 10번의 대화 기회
            is_first_encounter=True,
            memory_data=MemoryData()  # 빈 메모리 데이터 초기화
        )
        
        # 문명 정보 가져오기
        civ_info = await get_civilization_info(civilization_id)
        
        # 첫 메시지 생성
        initial_message = get_initial_message_by_traits(civ_info)
        
        # 메모리 초기화
        get_civilization_memory(session_id, civilization_id)
        
        # 세션 저장
        diplomacy_sessions[session_id] = new_session
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "session_id": session_id,
                    "player_name": player_name,
                    "civilization_name": civ_info["name"],
                    "initial_message": initial_message,
                    "remaining_interactions": 10
                },
                "error": None
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"서버 오류: {str(e)}", "data": None}
        )

# 메시지 전송 API
@router.post("/send-message", response_model=DiplomacyResponse)
async def send_message(request: DiplomacyRequest):
    """플레이어가 문명에게 메시지를 보냅니다."""
    try:
        player_name = request.player_name
        civilization_id = request.civilization_id
        message = request.message
        session_id = generate_session_id(player_name, civilization_id)
        
        # 세션 존재 확인
        if session_id not in diplomacy_sessions:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "외교 세션을 찾을 수 없습니다.", "data": None}
            )
        
        session = diplomacy_sessions[session_id]
        
        # 대화 가능 횟수 확인
        if session.remaining_interactions <= 0:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False, 
                    "error": "더 이상 대화할 수 없습니다.", 
                    "data": {
                        "can_interact_again_turn": session.can_interact_again_turn
                    }
                }
            )
        
        # 사용자 메시지 추가
        timestamp = datetime.now().isoformat()
        user_message = Message(role="user", content=message, timestamp=timestamp)
        session.messages.append(user_message)
        
        # LLM을 사용하여 응답 생성
        response_content = await generate_llm_response(session_id, session.messages, civilization_id)
        
        # 응답 메시지 추가
        ai_message = Message(role="assistant", content=response_content, timestamp=datetime.now().isoformat())
        session.messages.append(ai_message)
        
        # 문명 정보 가져오기
        civ_info = await get_civilization_info(civilization_id)
        
        # 대화 메모리 업데이트
        session.memory_data = summarize_conversation(session.messages, civ_info)
        
        # 관계 점수 계산 및 업데이트
        old_score = session.relationship_score
        session.relationship_score = calculate_relationship_score(
            session.messages, 
            session.relationship_score, 
            session.memory_data
        )
        score_increase = session.relationship_score - old_score
        
        # 세션 업데이트
        session.last_interaction = datetime.now().isoformat()
        session.remaining_interactions -= 1
        
        # 점수 상한 제한 (100점 이하)
        session.relationship_score = min(session.relationship_score, 100)
        
        # 마지막 대화인 경우 다음 대화 가능 턴 설정
        if session.remaining_interactions == 0:
            # 다음 대화 가능 턴 설정 (예: 5턴 후)
            session.can_interact_again_turn = request.game_id + 5
        
        # 세션 저장
        diplomacy_sessions[session_id] = session
        
        # 사용자 메시지 개수 파악 (role이 user인 메시지 개수)
        user_message_count = sum(1 for msg in session.messages if msg.role == "user")
        
        # 응답 데이터 준비 (HTTP API)
        response_data = {
            "message": ai_message.content,
            "remaining_interactions": session.remaining_interactions
        }
        
        # 3번째 메시지 이후부터는 관계 점수 정보 포함
        if user_message_count >= 3:
            response_data.update({
                "relationship_score": session.relationship_score,
                "score_change": score_increase,
                "memory_summary": session.memory_data.summary if session.memory_data else "",
                "sentiment": session.memory_data.sentiment if session.memory_data else "neutral"
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": response_data,
                "error": None
            }
        )
        
    except Exception as e:
        import traceback
        print(f"메시지 전송 오류: {str(e)}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"서버 오류: {str(e)}", "data": None}
        )

# 외교 재개 API
@router.post("/resume-diplomacy", response_model=DiplomacyResponse)
async def resume_diplomacy(request: DiplomacyRequest):
    """일정 턴이 지난 후 외교를 재개합니다."""
    try:
        player_name = request.player_name
        civilization_id = request.civilization_id
        game_id = request.game_id  # 현재 턴
        session_id = generate_session_id(player_name, civilization_id)
        
        # 세션 존재 확인
        if session_id not in diplomacy_sessions:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "외교 세션을 찾을 수 없습니다.", "data": None}
            )
        
        session = diplomacy_sessions[session_id]
        
        # 대화 가능 여부 확인
        if session.can_interact_again_turn is None or game_id < session.can_interact_again_turn:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False, 
                    "error": f"아직 대화를 재개할 수 없습니다. {session.can_interact_again_turn}턴 이후에 가능합니다.", 
                    "data": {"can_interact_again_turn": session.can_interact_again_turn}
                }
            )
        
        # 세션 업데이트
        session.remaining_interactions = 5  # 재개 시 5번의 대화 기회
        session.is_first_encounter = False
        session.last_interaction = datetime.now().isoformat()
        session.can_interact_again_turn = None
        
        # 문명 정보 가져오기
        civ_info = await get_civilization_info(civilization_id)
        
        # 메모리 데이터가 없는 경우 초기화
        if not session.memory_data:
            session.memory_data = summarize_conversation(session.messages, civ_info)
        
        # 메모리에 재개 정보 추가
        if session.memory_data:
            if "재개" not in session.memory_data.key_points:
                session.memory_data.key_points.append("외교 관계가 재개되었습니다.")
                if len(session.memory_data.key_points) > 5:
                    session.memory_data.key_points = session.memory_data.key_points[-5:]  # 최대 5개 유지
        
        # 세션 저장
        diplomacy_sessions[session_id] = session
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "session_id": session_id,
                    "civilization_name": civ_info["name"],
                    "relationship_score": session.relationship_score,
                    "remaining_interactions": session.remaining_interactions,
                    "previous_messages": [
                        {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
                        for msg in session.messages[-6:]  # 최근 6개 메시지만 반환
                    ],
                    "memory_data": {
                        "summary": session.memory_data.summary if session.memory_data else "",
                        "key_points": session.memory_data.key_points if session.memory_data else [],
                        "last_topics": session.memory_data.last_topics if session.memory_data else [],
                        "sentiment": session.memory_data.sentiment if session.memory_data else "neutral"
                    }
                },
                "error": None
            }
        )
        
    except Exception as e:
        import traceback
        print(f"외교 재개 오류: {str(e)}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"서버 오류: {str(e)}", "data": None}
        )

# 관계 점수 조회 API
@router.get("/{player_name}/relationship/{civilization_id}", response_model=DiplomacyResponse)
async def get_relationship_score(player_name: str, civilization_id: int):
    """특정 문명과의 관계 점수를 조회합니다."""
    try:
        session_id = generate_session_id(player_name, civilization_id)
        
        # 세션 존재 확인
        if session_id not in diplomacy_sessions:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "외교 세션을 찾을 수 없습니다.", "data": None}
            )
        
        session = diplomacy_sessions[session_id]
        
        # 문명 정보 가져오기
        civ_info = await get_civilization_info(civilization_id)
        
        # 메모리 데이터 준비
        memory_info = {}
        if session.memory_data:
            memory_info = {
                "summary": session.memory_data.summary,
                "key_points": session.memory_data.key_points,
                "last_topics": session.memory_data.last_topics,
                "sentiment": session.memory_data.sentiment
            }
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "civilization_id": civilization_id,
                    "civilization_name": civ_info["name"],
                    "relationship_score": session.relationship_score,
                    "last_interaction": session.last_interaction,
                    "can_interact": session.remaining_interactions > 0 or session.can_interact_again_turn is None or session.can_interact_again_turn <= 0,
                    "can_interact_again_turn": session.can_interact_again_turn,
                    "memory_data": memory_info
                },
                "error": None
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"서버 오류: {str(e)}", "data": None}
        )

# 대화 기록 조회 API
@router.get("/{player_name}/history/{civilization_id}", response_model=DiplomacyResponse)
async def get_conversation_history(player_name: str, civilization_id: int, limit: int = Query(10, ge=1, le=50)):
    """특정 문명과의 대화 기록을 조회합니다."""
    try:
        session_id = generate_session_id(player_name, civilization_id)
        
        # 세션 존재 확인
        if session_id not in diplomacy_sessions:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "외교 세션을 찾을 수 없습니다.", "data": None}
            )
        
        session = diplomacy_sessions[session_id]
        
        # 최근 메시지 가져오기
        recent_messages = session.messages[-limit:] if limit > 0 else session.messages
        
        # 메모리 데이터 준비
        memory_info = {}
        if session.memory_data:
            memory_info = {
                "summary": session.memory_data.summary,
                "key_points": session.memory_data.key_points,
                "last_topics": session.memory_data.last_topics,
                "sentiment": session.memory_data.sentiment
            }
        
        # 문명 정보 가져오기
        civ_info = await get_civilization_info(civilization_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "civilization_id": civilization_id,
                    "civilization_name": civ_info["name"],
                    "messages": [
                        {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
                        for msg in recent_messages
                    ],
                    "relationship_score": session.relationship_score,
                    "memory_data": memory_info,
                    "message_count": len(session.messages),
                    "displayed_count": len(recent_messages)
                },
                "error": None
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"서버 오류: {str(e)}", "data": None}
        )

# 모든 문명과의 관계 조회 API
@router.get("/{player_name}/all-relationships", response_model=DiplomacyResponse)
async def get_all_relationships(player_name: str):
    """플레이어가 조우한 모든 문명과의 관계를 조회합니다."""
    try:
        # player_name으로 시작하는 세션 찾기
        safe_name = "".join(c for c in player_name if c.isalnum())
        prefix = f"dipl_{safe_name}_"
        player_sessions = {
            k: v for k, v in diplomacy_sessions.items() 
            if k.startswith(prefix)
        }
        
        relationships = []
        
        for session_id, session in player_sessions.items():
            civ_id = session.civilization_id
            civ_info = await get_civilization_info(civ_id)
            
            # 메모리 정보 추가
            memory_summary = ""
            sentiment = "neutral"
            if session.memory_data:
                memory_summary = session.memory_data.summary
                sentiment = session.memory_data.sentiment
                
            relationships.append({
                "civilization_id": civ_id,
                "civilization_name": civ_info["name"],
                "relationship_score": session.relationship_score,
                "last_interaction": session.last_interaction,
                "can_interact": session.remaining_interactions > 0 or session.can_interact_again_turn is None or session.can_interact_again_turn <= 0,
                "can_interact_again_turn": session.can_interact_again_turn,
                "memory_summary": memory_summary,
                "sentiment": sentiment
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "player_name": player_name,
                    "session_count": len(relationships),
                    "relationships": relationships
                },
                "error": None
            }
        )
        
    except Exception as e:
        import traceback
        print(f"관계 조회 오류: {str(e)}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"서버 오류: {str(e)}", "data": None}
        ) 