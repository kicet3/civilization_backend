from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import List, Dict, Any, Optional
import json
import os
import httpx
import uuid
from datetime import datetime
from pydantic import BaseModel
import asyncio
# LangChain 관련 임포트 수정
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
# Ollama 관련 임포트는 유지 (필요할 수 있으므로)
from langchain_ollama import ChatOllama

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
    """LangChain을 사용하여 Gemini API를 호출하여 응답을 생성합니다."""
    try:
        # Gemini 모델 설정
        google_api_key = os.getenv("GOOGLE_API_KEY")
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
        
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
            city_info = "\n".join([f"- {city.get('name', '이름 없음')}: 인구 {city.get('population', '정보 없음')}, "
                                  f"건설 중: {city.get('in_progress', {}).get('building', '없음')}"
                                  for city in cities])
            
            context_update = f"""
현재 게임 상태 업데이트:
턴: {game_state.get('turn', '정보 없음')}
시대: {game_state.get('era', '정보 없음')}
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
        
        # LangChain 메시지 형식으로 변환
        langchain_messages = []
        
        for msg in conversation:
            if msg["role"] == "system":
                langchain_messages.append(SystemMessage(content=msg["content"]))
            elif msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
        
        # 마지막 메시지가 사용자의 현재 질문인지 확인
        if not langchain_messages or langchain_messages[-1].type != "human" or langchain_messages[-1].content != user_message:
            langchain_messages.append(HumanMessage(content=user_message))
        
        try:
            # 환경 변수 확인
            if not google_api_key:
                print("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
                raise ValueError("Google API Key가 설정되지 않았습니다.")
            
            # 채팅에서는 Gemini 사용
            print(f"채팅 대화를 위해 Gemini 모델({gemini_model}) 사용")
            chat_model = ChatGoogleGenerativeAI(
                model=gemini_model,
                google_api_key=google_api_key,
                temperature=0.7,
                top_p=0.95,
                top_k=40,
                convert_system_message_to_human=True  # Gemini는 SystemMessage를 직접 처리하지 않음
            )
            
            # LLM 호출
            response = chat_model.invoke(langchain_messages)
            
            # 응답 텍스트 추출
            response_text = response.content
            
            if not response_text:
                print("Gemini 응답에 텍스트가 없습니다.")
                return "죄송합니다. API에서 텍스트 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요."
            
            return response_text
            
        except Exception as e:
            print(f"Gemini 모델 호출 오류: {str(e)}")
            
            # Gemini 호출 실패 시 예비로 Ollama 사용 시도
            try:
                # Ollama 설정
                ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
                ollama_model = os.getenv("OLLAMA_MODEL", "eeve-korean-10.8b") 
                
                print(f"Gemini 호출 실패로 인한 Ollama 모델({ollama_model}) 백업 사용")
                chat_model = ChatOllama(
                    model=ollama_model,
                    base_url=ollama_url,
                    temperature=0.7,
                    top_p=0.8,
                    top_k=40,
                    num_predict=1000,
                )
                
                # LLM 호출
                response = chat_model.invoke(langchain_messages)
                
                # 응답 텍스트 추출
                response_text = response.content
                
                if response_text:
                    return response_text
            except Exception as e2:
                print(f"Ollama 백업 호출도 실패: {str(e2)}")
            
            # 오류 발생 시 백업으로 개발 모드 응답 사용
            if os.getenv("ENVIRONMENT", "development") == "development":
                print("개발 모드에서 백업 응답을 사용합니다.")
                backup_responses = [
                    "문명 게임에서는 균형 잡힌 개발이 중요합니다. 과학, 문화, 군사력을 골고루 발전시키세요.",
                    "초기에는 도시 개발과 정착민 생산에 집중하는 것이 좋습니다.",
                    "자원 타일 위에 도시를 건설하면 해당 자원을 바로 활용할 수 있습니다.",
                    "다른 문명과의 외교 관계를 잘 관리하세요. 무역로를 설정하면 경제적 이득을 얻을 수 있습니다.",
                    "군사 유닛을 적절히 배치하여 도시와 국경을 방어하세요.",
                    "연구 기술을 선택할 때는 현재 당신이 가장 필요로 하는 기술을 우선적으로 연구하세요."
                ]
                import random
                return random.choice(backup_responses)
            
            return f"죄송합니다. LLM 호출 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (오류: {str(e)})"
        
    except Exception as e:
        import traceback
        print(f"LLM 응답 생성 오류: {str(e)}")
        print(traceback.format_exc())  # 상세 오류 스택트레이스 출력
        return f"죄송합니다. 응답을 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (오류: {str(e)})"
