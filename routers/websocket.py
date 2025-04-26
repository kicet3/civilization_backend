from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from pydantic import BaseModel, Field

router = APIRouter()

# 웹소켓 연결 관리자
class ConnectionManager:
    def __init__(self):
        # 활성화된 연결을 저장 {game_id: {player_id: WebSocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # 각 게임의 메시지 히스토리 저장
        self.message_history: Dict[str, List[Dict[str, Any]]] = {}
        
    async def connect(self, websocket: WebSocket, game_id: str, player_id: str):
        """새로운 WebSocket 연결 추가"""
        await websocket.accept()
        
        # 게임 ID에 해당하는 딕셔너리가 없으면 생성
        if game_id not in self.active_connections:
            self.active_connections[game_id] = {}
            self.message_history[game_id] = []
            
        # 해당 플레이어 ID로 웹소켓 저장
        self.active_connections[game_id][player_id] = websocket
        
        # 접속 메시지 생성 및 브로드캐스트
        connection_msg = {
            "type": "player_connected",
            "player_id": player_id,
            "timestamp": datetime.now().isoformat(),
            "content": f"Player {player_id} connected to game {game_id}"
        }
        
        # 접속 히스토리에 저장
        self.message_history[game_id].append(connection_msg)
        
        # 해당 게임의 모든 플레이어에게 접속 알림
        await self.broadcast(game_id, connection_msg)
        
        # 접속한 플레이어에게 이전 메시지 히스토리 전송
        await self.send_history(websocket, game_id)
    
    async def disconnect(self, game_id: str, player_id: str):
        """WebSocket 연결 제거"""
        if game_id in self.active_connections and player_id in self.active_connections[game_id]:
            # 연결 종료 메시지 생성
            disconnect_msg = {
                "type": "player_disconnected",
                "player_id": player_id,
                "timestamp": datetime.now().isoformat(),
                "content": f"Player {player_id} disconnected from game {game_id}"
            }
            
            # 히스토리에 저장
            if game_id in self.message_history:
                self.message_history[game_id].append(disconnect_msg)
            
            # 먼저 웹소켓 참조 저장 후 삭제
            try:
                # 다른 사람들에게 알리고
                await self.broadcast_except_sender(game_id, player_id, disconnect_msg)
            except Exception as e:
                print(f"Error broadcasting disconnect message: {str(e)}")
            
            # 유저 연결 삭제
            del self.active_connections[game_id][player_id]
            
            # 게임에 더 이상 연결된 플레이어가 없으면 게임 정보 삭제
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]
                if game_id in self.message_history:
                    del self.message_history[game_id]
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """특정 웹소켓 연결에만 메시지 전송"""
        await websocket.send_text(json.dumps(message))
    
    async def broadcast(self, game_id: str, message: Dict[str, Any]):
        """게임에 연결된 모든, 플레이어에게 메시지 브로드캐스트"""
        if game_id in self.active_connections:
            for player_websocket in self.active_connections[game_id].values():
                await player_websocket.send_text(json.dumps(message))
    
    async def broadcast_except_sender(self, game_id: str, sender_id: str, message: Dict[str, Any]):
        """송신자를 제외한 모든 플레이어에게 메시지 브로드캐스트"""
        if game_id in self.active_connections:
            for player_id, websocket in self.active_connections[game_id].items():
                if player_id != sender_id:
                    await websocket.send_text(json.dumps(message))
    
    async def send_history(self, websocket: WebSocket, game_id: str):
        """연결된 클라이언트에게 메시지 히스토리 전송"""
        if game_id in self.message_history:
            history_message = {
                "type": "message_history",
                "timestamp": datetime.now().isoformat(),
                "messages": self.message_history[game_id]
            }
            await websocket.send_text(json.dumps(history_message))

# 웹소켓 연결 관리자 인스턴스 생성
manager = ConnectionManager()

# 메시지 타입 정의
class MessageType:
    CHAT = "chat"
    GAME_ACTION = "game_action"
    UNIT_MOVE = "unit_move"
    CITY_ACTION = "city_action"
    TECH_RESEARCH = "tech_research"
    TURN_END = "turn_end"
    SYSTEM = "system"

# 웹소켓 전송용 메시지 모델
class WebSocketMessage(BaseModel):
    type: str
    game_id: str
    player_id: str
    content: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

@router.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, player_id: str):
    """웹소켓 연결 엔드포인트"""
    try:
        # 연결 성공 여부를 검사하지 않고 무조건 accept
        await websocket.accept()
        
        # 게임 ID 검증 로직 추가 (필요한 경우)
        # 간단한 검증: 게임 ID는 UUID 형식(36자)
        if len(game_id) != 36 and not game_id.startswith("test_"):
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Invalid game ID format"
            }))
            await websocket.close()
            return
            
        # 플레이어 ID 검증 로직 (필요한 경우)
        # 길이 체크 등 간단한 검증
        if len(player_id) < 5:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Invalid player ID format"
            }))
            await websocket.close()
            return
            
        # 검증 통과 후 ConnectionManager에 연결 추가
        if game_id not in manager.active_connections:
            manager.active_connections[game_id] = {}
            manager.message_history[game_id] = []
            
        # 해당 플레이어 ID로 웹소켓 저장
        manager.active_connections[game_id][player_id] = websocket
        
        # 접속 메시지 생성 및 브로드캐스트
        connection_msg = {
            "type": "player_connected",
            "player_id": player_id,
            "timestamp": datetime.now().isoformat(),
            "content": f"Player {player_id} connected to game {game_id}"
        }
        
        # 접속 히스토리에 저장
        manager.message_history[game_id].append(connection_msg)
        
        # 해당 게임의 모든 플레이어에게 접속 알림
        await manager.broadcast(game_id, connection_msg)
        
        # 접속한 플레이어에게 이전 메시지 히스토리 전송
        await manager.send_history(websocket, game_id)
        
        while True:
            # 클라이언트로부터 메시지 수신 (ping/pong도 처리)
            data = await websocket.receive_text()
            
            # ping 메시지 처리
            if data == "ping":
                # pong 응답
                await websocket.send_text("pong")
                continue
                
            # JSON 파싱
            try:
                message_data = json.loads(data)
                # 타입, 내용 확인
                message_type = message_data.get("type", "")
                content = message_data.get("content", {})
                
                # 메시지 객체 생성
                message = {
                    "type": message_type,
                    "player_id": player_id,
                    "timestamp": datetime.now().isoformat(),
                    "content": content
                }
                
                # 메시지 히스토리에 저장
                if game_id in manager.message_history:
                    manager.message_history[game_id].append(message)
                
                # 메시지 타입에 따라 다르게 처리
                if message_type == MessageType.CHAT:
                    # 채팅 메시지는 모든 플레이어에게 전송
                    await manager.broadcast(game_id, message)
                    
                elif message_type == MessageType.UNIT_MOVE:
                    # 유닛 이동 메시지
                    unit_id = content.get("unit_id")
                    to_q = content.get("to_q")
                    to_r = content.get("to_r")
                    to_s = content.get("to_s")
                    
                    if unit_id and to_q is not None and to_r is not None and to_s is not None:
                        # 게임 로직에 따른 유닛 이동 처리
                        # TODO: 실제 게임 로직과 연결
                        
                        # 이동 결과를 모든 플레이어에게 브로드캐스트
                        await manager.broadcast(game_id, message)
                
                elif message_type == MessageType.TURN_END:
                    # 턴 종료 메시지는 시스템 처리 후 모든 플레이어에게 전송
                    # TODO: 턴 종료 로직 구현
                    
                    # 턴 종료를 모든 플레이어에게 알림
                    await manager.broadcast(game_id, message)
                
                else:
                    # 기타 게임 액션
                    await manager.broadcast(game_id, message)
                
            except json.JSONDecodeError:
                # JSON 형식이 아닌 경우 에러 메시지 전송 (ping은 제외)
                if data != "ping":
                    error_message = {
                        "type": "error",
                        "player_id": "system",
                        "timestamp": datetime.now().isoformat(),
                        "content": {"error": "Invalid message format. JSON expected."}
                    }
                    await manager.send_personal_message(error_message, websocket)
                
    except WebSocketDisconnect:
        # 연결이 끊어진 경우 처리
        if game_id in manager.active_connections and player_id in manager.active_connections[game_id]:
            await manager.disconnect(game_id, player_id)
    except Exception as e:
        # 기타 예외 처리
        print(f"WebSocket error: {str(e)}")
        try:
            if game_id in manager.active_connections and player_id in manager.active_connections[game_id]:
                await manager.disconnect(game_id, player_id)
        except:
            pass

# 게임 이벤트 수동 전송 엔드포인트 (서버에서 이벤트 발생 시 사용)
@router.post("/game/{game_id}/event")
async def send_game_event(game_id: str, event: WebSocketMessage):
    """게임 이벤트를 웹소켓을 통해 전송"""
    message = {
        "type": event.type,
        "player_id": event.player_id,
        "timestamp": event.timestamp.isoformat(),
        "content": event.content
    }
    
    # 메시지 히스토리에 저장
    if game_id in manager.message_history:
        manager.message_history[game_id].append(message)
    
    # 모든 플레이어에게 브로드캐스트
    await manager.broadcast(game_id, message)
    
    return {"status": "success", "message": "Event broadcast successfully"}

# 게임 정보 조회 엔드포인트
@router.get("/game/{game_id}/connections")
async def get_game_connections(game_id: str):
    """현재 게임에 연결된 플레이어 정보 조회"""
    if game_id not in manager.active_connections:
        return {"status": "not_found", "message": "Game not found"}
    
    connected_players = list(manager.active_connections[game_id].keys())
    return {
        "status": "success", 
        "game_id": game_id,
        "connected_players": connected_players,
        "total_connections": len(connected_players)
    } 