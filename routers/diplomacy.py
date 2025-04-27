from fastapi import APIRouter, HTTPException, Depends, Query
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

# API 라우터 설정
router = APIRouter(
    prefix="/diplomacy",
    tags=["diplomacy"],
    responses={404: {"description": "Not found"}},
)

# 모델 정의
class Message(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None

class DiplomacySession(BaseModel):
    session_id: str
    civilization_id: int
    player_id: int
    messages: List[Message]
    last_interaction: str
    relationship_score: int
    remaining_interactions: int
    is_first_encounter: bool
    can_interact_again_turn: Optional[int] = None

class DiplomacyRequest(BaseModel):
    game_id: int
    player_id: int
    civilization_id: int
    message: Optional[str] = None

class DiplomacyResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# 메모리 저장소 (실제 구현에서는 데이터베이스 사용을 권장)
diplomacy_sessions: Dict[str, DiplomacySession] = {}

# 세션 ID 생성 함수
def generate_session_id(player_id: int, civilization_id: int) -> str:
    return f"dipl_{player_id}_{civilization_id}"

# 기본 시스템 프롬프트
SYSTEM_PROMPT = """당신은 문명 게임에서 AI 문명의 외교관 역할을 맡고 있습니다.
플레이어와의 대화를 통해 관계를 형성하고, 문명의 특성과 성격에 맞게 응답해야 합니다.
문명마다 고유한 특성과 성격이 있으며, 이에 따라 대화 스타일과 태도가 달라집니다.
대화를 통해 플레이어와의 관계 점수가 결정되며, 점수에 따라 향후 외교 관계에 영향을 미칩니다.
답변은 짧고 간결하게 하되, 문명의 특성을 잘 반영해야 합니다.
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

# LLM 응답 생성 함수
async def generate_llm_response(messages: List[Message], civilization_id: int) -> str:
    """LLM을 통해 응답을 생성하는 함수"""
    
    api_key = os.getenv("GOOGLE_API_KEY", "YOUR_GOOGLE_API_KEY")
    api_url = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models")
    model = os.getenv("GEMINI_MODEL", "gemini-pro")
    
    # 문명 정보 추가
    civ_info = CIVILIZATION_TRAITS.get(civilization_id, {"name": "알 수 없는 문명", "trait": "", "personality": ""})
    
    # 시스템 프롬프트 조정
    system_prompt = f"{SYSTEM_PROMPT}\n\n당신은 {civ_info['name']} 문명의 외교관입니다.\n{civ_info['trait']}\n성격: {civ_info['personality']}"
    
    # Gemini API가 시스템 역할을 직접 지원하지 않으므로 첫 번째 사용자 메시지로 변환
    gemini_messages = []
    
    # 시스템 메시지를 첫 번째 사용자 메시지로 추가
    gemini_messages.append({
        "role": "user",
        "parts": [{"text": system_prompt}]
    })
    
    # 첫 번째 시스템 메시지 응답으로 빈 응답 추가
    gemini_messages.append({
        "role": "model",
        "parts": [{"text": "이해했습니다. 저는 이제 해당 문명의 외교관 역할을 수행하겠습니다."}]
    })
    
    # 나머지 대화 메시지 추가
    for msg in messages:
        role = "user" if msg.role == "user" else "model"
        gemini_messages.append({
            "role": role,
            "parts": [{"text": msg.content}]
        })
    
    try:
        full_url = f"{api_url}/{model}:generateContent"
        
        request_data = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 500
            }
        }
        
        # 개발 환경에서 API 호출 대신 모의 응답
        if os.getenv("ENVIRONMENT", "development") == "development":
            # 개발 환경에서는 모의 응답 반환
            mock_responses = [
                f"{civ_info['name']} 문명이 당신을 환영합니다. 우리는 평화로운 관계를 희망합니다.",
                f"흥미로운 제안입니다. {civ_info['name']} 문명은 이를 고려해 보겠습니다.",
                f"당신의 문명은 우리에게 위협이 될 수 있습니다. 조심스럽게 진행하겠습니다.",
                f"우리 {civ_info['name']} 문명은 당신과의 무역에 관심이 있습니다.",
                f"우리의 군사력은 과소평가하지 않는 것이 좋을 것입니다.",
                f"우리 문명의 문화와 전통을 존중해 주시기 바랍니다."
            ]
            return random.choice(mock_responses)
        
        # 실제 환경에서는 API 호출
        async with httpx.AsyncClient() as client:
            response = await client.post(
                full_url,
                params={"key": api_key},
                json=request_data,
                timeout=30.0
            )
            
            if response.status_code != 200:
                print(f"API Error: {response.status_code}, {response.text}")
                return "죄송합니다, 응답을 생성하는 데 문제가 발생했습니다."
            
            response_data = response.json()
            return response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "응답 없음")
            
    except Exception as e:
        print(f"Error generating LLM response: {str(e)}")
        return "죄송합니다, 응답을 생성하는 데 문제가 발생했습니다."

# 관계 점수 계산 함수
def calculate_relationship_score(messages: List[Message]) -> int:
    """대화 내용을 기반으로 관계 점수를 계산하는 함수"""
    # 기본 점수 30에서 시작
    score = 30
    
    # 메시지 수에 따라 점수 증가 (최대 10점)
    user_messages = [msg for msg in messages if msg.role == "user"]
    score += min(len(user_messages), 10)
    
    # 긍정적/부정적 키워드에 따른 점수 조정
    positive_keywords = ["동맹", "친구", "협력", "평화", "무역", "도움", "지원", "감사", "존중"]
    negative_keywords = ["전쟁", "공격", "위협", "적", "파괴", "침략", "배신", "거부", "무시"]
    
    for msg in user_messages:
        content = msg.content.lower()
        for keyword in positive_keywords:
            if keyword in content:
                score += random.randint(3, 5)
        for keyword in negative_keywords:
            if keyword in content:
                score -= 2
    
    # 점수 범위 제한 (0-100)
    score = max(0, min(score, 100))
    
    return score

# 첫 번째 조우 처리 API
@router.post("/first-encounter", response_model=DiplomacyResponse)
async def first_encounter(request: DiplomacyRequest):
    """플레이어가 새로운 문명을 처음 조우했을 때의 처리"""
    try:
        player_id = request.player_id
        civilization_id = request.civilization_id
        session_id = generate_session_id(player_id, civilization_id)
        
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
            player_id=player_id,
            messages=[],
            last_interaction=datetime.now().isoformat(),
            relationship_score=30,  # 초기 점수를 30으로 변경
            remaining_interactions=10,  # 첫 조우 시 10번의 대화 기회
            is_first_encounter=True
        )
        
        # 문명 정보 가져오기
        civ_info = CIVILIZATION_TRAITS.get(civilization_id, {"name": "알 수 없는 문명"})
        
        # 첫 메시지 생성
        initial_message = f"{civ_info['name']} 문명을 발견했습니다! 외교관이 당신과 대화하기를 원합니다."
        
        # 세션 저장
        diplomacy_sessions[session_id] = new_session
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "session_id": session_id,
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
        player_id = request.player_id
        civilization_id = request.civilization_id
        message = request.message
        session_id = generate_session_id(player_id, civilization_id)
        
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
        response_content = await generate_llm_response(session.messages, civilization_id)
        
        # 응답 메시지 추가
        ai_message = Message(role="assistant", content=response_content, timestamp=datetime.now().isoformat())
        session.messages.append(ai_message)
        
        # 세션 업데이트
        session.last_interaction = datetime.now().isoformat()
        session.remaining_interactions -= 1
        
        # 관계 점수 랜덤 상승 (3~5점)
        score_increase = random.randint(3, 5)
        session.relationship_score += score_increase
        
        # 점수 상한 제한 (100점 이하)
        session.relationship_score = min(session.relationship_score, 100)
        
        # 마지막 대화인 경우 다음 대화 가능 턴 설정
        if session.remaining_interactions == 0:
            # 다음 대화 가능 턴 설정 (예: 5턴 후)
            session.can_interact_again_turn = request.game_id + 5
        
        # 세션 저장
        diplomacy_sessions[session_id] = session
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "message": ai_message.content,
                    "remaining_interactions": session.remaining_interactions,
                    "relationship_score": session.relationship_score,
                    "score_increase": score_increase
                },
                "error": None
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"서버 오류: {str(e)}", "data": None}
        )

# 외교 재개 API
@router.post("/resume-diplomacy", response_model=DiplomacyResponse)
async def resume_diplomacy(request: DiplomacyRequest):
    """일정 턴이 지난 후 외교를 재개합니다."""
    try:
        player_id = request.player_id
        civilization_id = request.civilization_id
        game_id = request.game_id  # 현재 턴
        session_id = generate_session_id(player_id, civilization_id)
        
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
        civ_info = CIVILIZATION_TRAITS.get(civilization_id, {"name": "알 수 없는 문명"})
        
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
                    ]
                },
                "error": None
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"서버 오류: {str(e)}", "data": None}
        )

# 관계 점수 조회 API
@router.get("/{player_id}/relationship/{civilization_id}", response_model=DiplomacyResponse)
async def get_relationship_score(player_id: int, civilization_id: int):
    """특정 문명과의 관계 점수를 조회합니다."""
    try:
        session_id = generate_session_id(player_id, civilization_id)
        
        # 세션 존재 확인
        if session_id not in diplomacy_sessions:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "외교 세션을 찾을 수 없습니다.", "data": None}
            )
        
        session = diplomacy_sessions[session_id]
        
        # 문명 정보 가져오기
        civ_info = CIVILIZATION_TRAITS.get(civilization_id, {"name": "알 수 없는 문명"})
        
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
                    "can_interact_again_turn": session.can_interact_again_turn
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
@router.get("/{player_id}/history/{civilization_id}", response_model=DiplomacyResponse)
async def get_conversation_history(player_id: int, civilization_id: int, limit: int = Query(10, ge=1, le=50)):
    """특정 문명과의 대화 기록을 조회합니다."""
    try:
        session_id = generate_session_id(player_id, civilization_id)
        
        # 세션 존재 확인
        if session_id not in diplomacy_sessions:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "외교 세션을 찾을 수 없습니다.", "data": None}
            )
        
        session = diplomacy_sessions[session_id]
        
        # 최근 메시지 가져오기
        recent_messages = session.messages[-limit:] if limit > 0 else session.messages
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "civilization_id": civilization_id,
                    "messages": [
                        {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
                        for msg in recent_messages
                    ],
                    "relationship_score": session.relationship_score
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
@router.get("/{player_id}/all-relationships", response_model=DiplomacyResponse)
async def get_all_relationships(player_id: int):
    """플레이어가 조우한 모든 문명과의 관계를 조회합니다."""
    try:
        player_sessions = {
            k: v for k, v in diplomacy_sessions.items() 
            if k.startswith(f"dipl_{player_id}_")
        }
        
        relationships = []
        
        for session_id, session in player_sessions.items():
            civ_id = session.civilization_id
            civ_info = CIVILIZATION_TRAITS.get(civ_id, {"name": "알 수 없는 문명"})
            
            relationships.append({
                "civilization_id": civ_id,
                "civilization_name": civ_info["name"],
                "relationship_score": session.relationship_score,
                "last_interaction": session.last_interaction,
                "can_interact": session.remaining_interactions > 0 or session.can_interact_again_turn is None or session.can_interact_again_turn <= 0,
                "can_interact_again_turn": session.can_interact_again_turn
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "player_id": player_id,
                    "relationships": relationships
                },
                "error": None
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"서버 오류: {str(e)}", "data": None}
        ) 