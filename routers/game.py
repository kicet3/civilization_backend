from typing import Optional
from fastapi import APIRouter, Query, Depends
import json
import hashlib
from db.client import get_prisma

router = APIRouter()

@router.get("/{game_id}")
async def get_game_state(
    game_id: str = None, 
    user_name: Optional[str] = Query(None, description="사용자 이름"),
    turn: Optional[int] = None
):
    """특정 게임의 상태 조회"""
    try:
        # 연결이 필요한 경우에만 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                # 실제 연결 오류인 경우에만 오류 반환
                if "Could not connect" in str(e):
                    return {
                        "success": False,
                        "status_code": 500,
                        "message": f"데이터베이스 연결 오류: {str(e)}",
                        "error": {
                            "type": type(e).__name__,
                            "detail": str(e)
                        }
                    }
            # 이미 연결된 경우는 무시
        
        # 게임 조회 조건 설정
        where_condition = {}
        
        # game_id가 제공된 경우
        if game_id:
            where_condition["id"] = game_id
        # user_name이 제공된 경우
        elif user_name:
            # 사용자 이름을 SHA256으로 해시
            user_name_hash = hashlib.sha256(user_name.encode()).hexdigest()
            where_condition["userName"] = user_name_hash
        # 둘 다 제공되지 않은 경우
        else:
            return {
                "success": False,
                "status_code": 400,
                "message": "게임 ID 또는 사용자 이름이 필요합니다."
            }
        
        # 게임 존재 여부 확인
        game = await prisma.game.find_first(
            where=where_condition,
            order={"createdAt": "desc"}  # 가장 최근 게임 조회
        )
        
        if not game:
            return {
                "success": False,
                "status_code": 404,
                "message": "해당 게임을 찾을 수 없습니다."
            }
        
        # 턴 번호 결정 (지정한 턴 또는 현재 턴)
        query_turn = turn if turn is not None else game.currentTurn
        
        # 게임 상태 조회
        game_state = await prisma.gamestate.find_first(
            where={
                "gameId": game.id,
                "turn": query_turn
            }
        )
        
        if not game_state:
            return {
                "success": False,
                "status_code": 404,
                "message": f"턴 {query_turn}의 게임 상태를 찾을 수 없습니다."
            }
        
        return {
            "success": True,
            "status_code": 200,
            "message": f"턴 {query_turn}의 게임 상태를 조회했습니다.",
            "data": game_state.stateData,
            "meta": {
                "game_id": game.id,
                "turn": query_turn,
                "current_turn": game.currentTurn,
                "created_at": game_state.createdAt.isoformat()
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "message": f"게임 상태 조회 중 오류가 발생했습니다: {str(e)}",
            "error": {
                "type": type(e).__name__,
                "detail": str(e)
            }
        }

@router.post("/{game_id}/turn/next")
async def next_turn(
    game_id: str = None,
    user_name: Optional[str] = Query(None, description="사용자 이름")
):
    """다음 턴으로 진행"""
    try:
        # 연결이 필요한 경우에만 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                # 실제 연결 오류인 경우에만 오류 반환
                if "Could not connect" in str(e):
                    return {
                        "success": False,
                        "status_code": 500,
                        "message": f"데이터베이스 연결 오류: {str(e)}",
                        "error": {
                            "type": type(e).__name__,
                            "detail": str(e)
                        }
                    }
            # 이미 연결된 경우는 무시
        
        # 게임 조회 조건 설정
        where_condition = {}
        
        # game_id가 제공된 경우
        if game_id:
            where_condition["id"] = game_id
        # user_name이 제공된 경우
        elif user_name:
            # 사용자 이름을 SHA256으로 해시
            user_name_hash = hashlib.sha256(user_name.encode()).hexdigest()
            where_condition["userName"] = user_name_hash
        # 둘 다 제공되지 않은 경우
        else:
            return {
                "success": False,
                "status_code": 400,
                "message": "게임 ID 또는 사용자 이름이 필요합니다."
            }
        
        # 1. 먼저 게임 정보 조회
        game = await prisma.game.find_first(
            where=where_condition,
            order={"createdAt": "desc"}  # 가장 최근 게임 조회
        )
        
        if not game:
            return {
                "success": False,
                "status_code": 404,
                "message": "해당 게임을 찾을 수 없습니다."
            }
        
        # 2. 현재 턴 정보로 게임 상태 조회
        current_turn = game.currentTurn
        
        game_states = await prisma.gamestate.find_many(
            where={
                "gameId": game.id,
                "turn": current_turn
            }
        )
        
        # 현재 게임 상태 가져오기
        if not game_states or len(game_states) == 0:
            return {
                "success": False,
                "status_code": 404,
                "message": "현재 턴의 게임 상태를 찾을 수 없습니다."
            }
        
        current_state = game_states[0]
        
        # 다음 턴으로 게임 상태 업데이트 (실제로는 턴 진행 로직 필요)
        # 여기서 AI들의 턴 처리, 자원 생산, 유닛 이동 등의 로직 처리
        
        # 다음 턴 번호
        next_turn_number = current_turn + 1
        
        # 새로운 게임 상태 생성 (이전 상태 복사 후 변경)
        new_state_data = current_state.stateData
        new_state_data["turn"] = next_turn_number
        
        # TODO: 여기서 게임 상태 업데이트 로직 구현
        # (자원 증가, AI 문명 움직임, 등)
        
        # 게임 업데이트
        updated_game = await prisma.game.update(
            where={"id": game.id},
            data={
                "currentTurn": next_turn_number
            }
        )
        
        # 새로운 게임 상태 별도 생성
        await prisma.gamestate.create(
            data={
                "gameId": game.id,
                "turn": next_turn_number,
                "phase": "ResourceCollection",
                "data": json.dumps(new_state_data)
            }
        )
    
        
        return {
            "success": True,
            "status_code": 200,
            "message": f"턴 {next_turn_number}로 진행되었습니다.",
            "data": {
                "game_id": game.id,
                "current_turn": next_turn_number,
                "state": new_state_data
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "message": f"턴 진행 중 오류가 발생했습니다: {str(e)}",
            "error": {
                "type": type(e).__name__,
                "detail": str(e)
            }
        }

@router.get("/games")
async def get_games():
    async with get_prisma() as db:
        games = await db.game.find_many()
        return games

@router.get("/games/{game_id}")
async def get_game(game_id: int):
    async with get_prisma() as db:
        game = await db.game.find_unique(
            where={
                'id': game_id
            }
        )
        return game
