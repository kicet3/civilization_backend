from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import List, Dict, Any, Optional
import json
import os
import httpx
import uuid
from datetime import datetime
from pydantic import BaseModel
import asyncio

router = APIRouter()

# 활성 연결 관리를 위한 클래스
class ConnectionManager:
    def __init__(self):
        # 연결 관리 (chat_id → WebSocket)
        self.active_connections: Dict[str, WebSocket] = {}
        # 대화 컨텍스트 관리 (chat_id → messages)
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        
    async def connect(self, websocket: WebSocket, chat_id: str):
        await websocket.accept()
        self.active_connections[chat_id] = websocket
        if chat_id not in self.conversations:
            self.conversations[chat_id] = []
            
    def disconnect(self, chat_id: str):
        if chat_id in self.active_connections:
            del self.active_connections[chat_id]
            
    async def send_message(self, chat_id: str, message: Dict[str, Any]):
        if chat_id in self.active_connections:
            await self.active_connections[chat_id].send_json(message)
            
    def add_message(self, chat_id: str, role: str, content: str):
        if chat_id not in self.conversations:
            self.conversations[chat_id] = []
            
        self.conversations[chat_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
    def get_conversation_history(self, chat_id: str) -> List[Dict[str, Any]]:
        return self.conversations.get(chat_id, [])

# 싱글톤 연결 관리자
manager = ConnectionManager()

# 시스템 프롬프트 템플릿
SYSTEM_PROMPT = """당신은 문명 게임 내의 AI 상담가이자 길잡이입니다. 
플레이어가 게임을 진행하면서 물어보는 질문에 답하고, 게임 전략적 조언을 제공합니다.

게임 규칙:
1. 플레이어는 한 문명을 이끌며 경쟁하는 다른 AI 문명들과 경쟁합니다.
2. 연구, 건설, 외교, 전쟁 등 다양한 방법으로 게임을 진행할 수 있습니다.
3. 시대는 고대, 중세, 산업 시대, 현대로 구분됩니다.
4. 각 시대마다 연구할 수 있는 기술과 건설할 수 있는 건물, 유닛이 다릅니다.

답변 시 주의사항:
1. 간결하고 명확하게 답변해주세요.
2. 게임 내 개념과 메커니즘을 설명할 때는 정확한 용어를 사용하세요.
3. 플레이어의 현재 게임 상황이 주어지면, 그에 맞는 맞춤형 조언을 제공하세요.
4. 어떤 전략이 더 효과적인지 상황에 맞게 제안하되, 최종 결정은 플레이어의 몫임을 존중하세요.

{additional_context}
"""

class LLMRequest(BaseModel):
    prompt: str
    game_state: Optional[Dict[str, Any]] = None
    
class ChatMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str

@router.websocket("/chat/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    """웹소켓을 통한 LLM 채팅 엔드포인트"""
    await manager.connect(websocket, chat_id)
    
    # 새로운 채팅인 경우 시스템 프롬프트 설정
    if not manager.get_conversation_history(chat_id):
        additional_context = "현재 게임에 대한 추가 정보가 없습니다. 일반적인 조언을 제공합니다."
        system_prompt = SYSTEM_PROMPT.format(additional_context=additional_context)
        manager.add_message(chat_id, "system", system_prompt)
        
    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            # 사용자 메시지 저장
            user_message = request_data.get("message", "")
            manager.add_message(chat_id, "user", user_message)
            
            # 게임 상태 정보 (있는 경우)
            game_state = request_data.get("game_state")
            
            # LLM 응답 생성
            response = await generate_llm_response(chat_id, user_message, game_state)
            
            # 응답 저장 및 전송
            manager.add_message(chat_id, "assistant", response)
            await manager.send_message(chat_id, {
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            
    except WebSocketDisconnect:
        manager.disconnect(chat_id)
    except Exception as e:
        error_message = f"오류 발생: {str(e)}"
        await manager.send_message(chat_id, {
            "role": "system",
            "content": error_message,
            "timestamp": datetime.now().isoformat(),
            "is_error": True
        })
        manager.disconnect(chat_id)

@router.post("/chat/init/{chat_id}")
async def initialize_chat(chat_id: str, game_state: Optional[Dict[str, Any]] = None):
    """새로운 채팅 세션 초기화"""
    # 게임 상태 정보가 있는 경우 추가 컨텍스트 구성
    if game_state:
        additional_context = f"""
현재 게임 상태:
- 턴: {game_state.get('turn', '정보 없음')}
- 시대: {game_state.get('era', '정보 없음')}
- 플레이어 문명: {game_state.get('player_civ', {}).get('name', '정보 없음')}
- 도시 수: {len(game_state.get('player_civ', {}).get('cities', []))}개
- 현재 연구 중인 기술: {game_state.get('player_civ', {}).get('research', {}).get('in_progress', {}).get('name', '없음')}
"""
    else:
        additional_context = "현재 게임에 대한 추가 정보가 없습니다. 일반적인 조언을 제공합니다."
    
    # 시스템 프롬프트 설정
    system_prompt = SYSTEM_PROMPT.format(additional_context=additional_context)
    
    # 새로운 대화 초기화
    if chat_id in manager.conversations:
        manager.conversations[chat_id] = []
    manager.add_message(chat_id, "system", system_prompt)
    
    return {
        "success": True,
        "chat_id": chat_id,
        "message": "채팅 세션이 초기화되었습니다."
    }

@router.get("/chat/history/{chat_id}")
async def get_chat_history(chat_id: str):
    """채팅 기록 조회"""
    history = manager.get_conversation_history(chat_id)
    return {
        "success": True,
        "chat_id": chat_id,
        "history": history
    }

async def generate_llm_response(chat_id: str, user_message: str, game_state: Optional[Dict[str, Any]] = None) -> str:
    """LLM API를 호출하여 응답을 생성합니다."""
    try:
        # Gemini API 설정
        api_key = os.getenv("GOOGLE_API_KEY", "YOUR_GOOGLE_API_KEY")
        api_url = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models")
        model = os.getenv("GEMINI_MODEL", "gemini-pro")
        
        # 대화 기록 가져오기
        conversation = manager.get_conversation_history(chat_id)
        
        # 게임 상태 정보가 있는 경우 컨텍스트 업데이트
        if game_state:
            # 플레이어 문명 정보
            player_civ = game_state.get("player_civ", {})
            
            # 현재 연구 상태
            research_status = player_civ.get("research", {})
            current_research = research_status.get("in_progress", {}).get("name", "없음")
            
            # 도시 정보
            cities = player_civ.get("cities", [])
            city_info = "\n".join([f"- {city.get('name')}: 인구 {city.get('population')}, "
                                  f"건설 중: {city.get('in_progress', {}).get('building', '없음')}"
                                  for city in cities])
            
            context_update = f"""
현재 게임 상태 업데이트:
턴: {game_state.get('turn')}
시대: {game_state.get('era')}
현재 연구 중인 기술: {current_research}

도시 정보:
{city_info}

이 정보를 바탕으로 플레이어의 질문에 답변해주세요.
"""
            # 시스템 메시지 업데이트
            system_found = False
            for msg in conversation:
                if msg["role"] == "system":
                    msg["content"] += f"\n\n{context_update}"
                    system_found = True
                    break
            
            if not system_found:
                # 시스템 메시지가 없으면 새로 추가
                additional_context = context_update
                system_prompt = SYSTEM_PROMPT.format(additional_context=additional_context)
                conversation.insert(0, {"role": "system", "content": system_prompt})
        
        # Gemini API 요청 형식 변환
        gemini_messages = []
        
        # 시스템 메시지 처리 (Gemini는 system role을 직접 지원하지 않으므로 user 메시지로 변환)
        system_content = ""
        for msg in conversation:
            if msg["role"] == "system":
                system_content = msg["content"]
                break
                
        if system_content:
            gemini_messages.append({
                "role": "user",
                "parts": [{"text": f"시스템 지침: {system_content}\n\n이제부터 이 지침에 따라 응답해주세요."}]
            })
            gemini_messages.append({
                "role": "model",
                "parts": [{"text": "네, 이해했습니다. 문명 게임의 AI 상담가로서 플레이어 질문에 답변하겠습니다."}]
            })
        
        # 나머지 대화 내용 변환
        for msg in conversation:
            if msg["role"] != "system":  # 시스템 메시지는 이미 처리함
                gemini_role = "user" if msg["role"] == "user" else "model"
                gemini_messages.append({
                    "role": gemini_role,
                    "parts": [{"text": msg["content"]}]
                })
                
        # API 요청 데이터 구성
        request_data = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 1000,
            }
        }
        
        # 실제 환경에서 Gemini API 호출
        complete_url = f"{api_url}/{model}:generateContent?key={api_key}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                complete_url,
                json=request_data,
                timeout=30.0
            )
            
            if response.status_code != 200:
                print(f"Gemini API 오류: {response.status_code} - {response.text}")
                return "죄송합니다. API 응답 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
                
            result = response.json()
            
            # Gemini API 응답 구조에서 텍스트 추출
            try:
                content = result.get("candidates", [])[0].get("content", {})
                text_parts = content.get("parts", [])
                response_text = "".join([part.get("text", "") for part in text_parts])
                return response_text
            except (KeyError, IndexError) as e:
                print(f"Gemini 응답 파싱 오류: {str(e)}, 응답: {result}")
                return "죄송합니다. 응답을 처리하는 중 오류가 발생했습니다."
        
    except Exception as e:
        print(f"LLM 응답 생성 오류: {str(e)}")
        return f"죄송합니다. 응답을 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
