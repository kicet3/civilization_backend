from typing import Optional
from fastapi import APIRouter, Query, Depends, Path
import json
import hashlib
import httpx
import random
import os
from typing import Dict, List, Any
from fastapi.responses import JSONResponse
from db.client import prisma, get_prisma

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
        
        # 다음 턴 번호
        next_turn_number = current_turn + 1
        
        # 새로운 게임 상태 생성 (이전 상태 복사 후 변경)
        new_state_data = current_state.stateData
        new_state_data["turn"] = next_turn_number
        
        # 게임 내 모든 문명 가져오기
        game_civs = await prisma.gameciv.find_many(
            where={
                "gameId": game.id
            }
        )
        
        # 플레이어 문명 ID 찾기 (나머지는 AI 문명으로 간주)
        player_civ_id = None
        ai_civ_ids = []
        
        for civ in game_civs:
            if civ.isPlayer:
                player_civ_id = civ.id
            else:
                ai_civ_ids.append(civ.id)
        
        # 플레이어 문명 업데이트
        if player_civ_id:
            # 1. 연구 진행 상태 업데이트
            await update_research_progress(player_civ_id)
            
            # 2. 도시 목록 가져오기
            player_cities = await prisma.city.find_many(
                where={
                    "gameCivId": player_civ_id
                }
            )
            
            # 3. 각 도시별 건물 건설 및 유닛 생산 업데이트
            for city in player_cities:
                await update_building_construction(city.id)
                # TODO: 유닛 생산 업데이트 로직 추가
        
        # AI 문명들의 행동 결정 및 처리
        for ai_civ_id in ai_civ_ids:
            # 해당 AI 문명의 정보 수집
            ai_civ = await get_civ_data(ai_civ_id)
            
            # LLM API 호출하여 AI 문명의 행동 결정
            ai_decisions = await get_ai_decisions(ai_civ, current_state.stateData, next_turn_number)
            
            # AI 결정사항 적용
            await apply_ai_decisions(ai_civ_id, ai_decisions)
        
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
                "stateData": new_state_data  # Prisma 모델에 맞게 필드명 수정
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

async def update_research_progress(game_civ_id: int):
    """문명의 연구 진행 상태를 업데이트합니다."""
    # 현재 연구 중인 기술 찾기
    in_progress = await prisma.gamecivtechnology.find_first(
        where={
            "gameCivId": game_civ_id,
            "status": "in_progress"
        }
    )
    
    if not in_progress:
        # 연구 중인 기술이 없으면 연구 큐에서 다음 기술 가져와서 연구 시작
        queue_entry = await prisma.researchqueue.find_first(
            where={
                "gameCivId": game_civ_id,
                "queuePosition": 1
            }
        )
        
        if queue_entry:
            # 큐에서 첫 번째 기술 가져와서 연구 시작
            tech_id = queue_entry.techId
            
            # 연구 시작
            existing_record = await prisma.gamecivtechnology.find_first(
                where={
                    "gameCivId": game_civ_id,
                    "techId": tech_id
                }
            )
            
            if existing_record:
                # 기존 레코드 업데이트
                await prisma.gamecivtechnology.update(
                    where={"id": existing_record.id},
                    data={
                        "status": "in_progress",
                        "startedAt": prisma.datetime.now()
                    }
                )
            else:
                # 새 레코드 생성
                await prisma.gamecivtechnology.create(
                    data={
                        "gameCivId": game_civ_id,
                        "techId": tech_id,
                        "status": "in_progress",
                        "progressPoints": 0,
                        "startedAt": prisma.datetime.now()
                    }
                )
            
            # 큐에서 제거
            await prisma.researchqueue.delete(
                where={"id": queue_entry.id}
            )
            
            # 나머지 큐 재정렬
            await prisma.researchqueue.update_many(
                where={
                    "gameCivId": game_civ_id,
                    "queuePosition": {
                        "gt": 1
                    }
                },
                data={
                    "queuePosition": {
                        "decrement": 1
                    }
                }
            )
        
        return
    
    # 연구 중인 기술이 있으면 진행도 업데이트
    # 기술 정보 조회
    tech = await prisma.technology.find_unique(
        where={"id": in_progress.techId}
    )
    
    if not tech:
        return
    
    # 문명 정보로 사이언스 포인트 계산 
    # 여기서는 임의의 값(10)을 사용, 실제로는 문명의 사이언스 산출량을 계산해야 함
    science_points = 10
    
    # 연구 진행도 업데이트
    new_progress_points = in_progress.progressPoints + science_points
    
    # 연구 완료 여부 확인
    if new_progress_points >= tech.researchCost:
        # 연구 완료 처리
        await prisma.gamecivtechnology.update(
            where={"id": in_progress.id},
            data={
                "status": "completed",
                "progressPoints": tech.researchCost,
                "completedAt": prisma.datetime.now()
            }
        )
        
        # 연구 큐에서 다음 기술 가져와서 연구 시작
        queue_entry = await prisma.researchqueue.find_first(
            where={
                "gameCivId": game_civ_id,
                "queuePosition": 1
            }
        )
        
        if queue_entry:
            # 큐에서 첫 번째 기술 가져와서 연구 시작
            next_tech_id = queue_entry.techId
            
            # 연구 시작
            existing_record = await prisma.gamecivtechnology.find_first(
                where={
                    "gameCivId": game_civ_id,
                    "techId": next_tech_id
                }
            )
            
            if existing_record:
                # 기존 레코드 업데이트
                await prisma.gamecivtechnology.update(
                    where={"id": existing_record.id},
                    data={
                        "status": "in_progress",
                        "progressPoints": 0,
                        "startedAt": prisma.datetime.now()
                    }
                )
            else:
                # 새 레코드 생성
                await prisma.gamecivtechnology.create(
                    data={
                        "gameCivId": game_civ_id,
                        "techId": next_tech_id,
                        "status": "in_progress",
                        "progressPoints": 0,
                        "startedAt": prisma.datetime.now()
                    }
                )
            
            # 큐에서 제거
            await prisma.researchqueue.delete(
                where={"id": queue_entry.id}
            )
            
            # 나머지 큐 재정렬
            await prisma.researchqueue.update_many(
                where={
                    "gameCivId": game_civ_id,
                    "queuePosition": {
                        "gt": 1
                    }
                },
                data={
                    "queuePosition": {
                        "decrement": 1
                    }
                }
            )
    else:
        # 연구 진행 중인 경우 진행도만 업데이트
        await prisma.gamecivtechnology.update(
            where={"id": in_progress.id},
            data={
                "progressPoints": new_progress_points
            }
        )

async def update_building_construction(city_id: int):
    """도시의 건물 건설 상태를 업데이트합니다."""
    # 현재 건설 중인 건물 찾기
    in_progress = await prisma.playerbuilding.find_first(
        where={
            "cityId": city_id,
            "status": "in_progress"
        }
    )
    
    if not in_progress:
        # 건설 중인 건물이 없으면 건설 큐에서 다음 건물 가져와서 건설 시작
        queue_entry = await prisma.buildqueue.find_first(
            where={
                "cityId": city_id,
                "queueOrder": 1
            }
        )
        
        if queue_entry:
            # 큐에서 첫 번째 건물 가져와서 건설 시작
            building_id = queue_entry.buildingId
            
            # 도시 정보 조회
            city = await prisma.city.find_unique(
                where={"id": city_id}
            )
            
            if not city:
                return
            
            # 건설 시작
            await prisma.playerbuilding.create(
                data={
                    "cityId": city_id,
                    "buildingId": building_id,
                    "gameCivId": city.gameCivId,
                    "status": "in_progress",
                    "startedAt": prisma.datetime.now()
                }
            )
            
            # 큐에서 제거
            await prisma.buildqueue.delete(
                where={"id": queue_entry.id}
            )
            
            # 나머지 큐 재정렬
            await prisma.buildqueue.update_many(
                where={
                    "cityId": city_id,
                    "queueOrder": {
                        "gt": 1
                    }
                },
                data={
                    "queueOrder": {
                        "decrement": 1
                    }
                }
            )
        
        return
    
    # 건설 중인 건물이 있으면 진행도 업데이트
    # 건물 정보 조회
    building = await prisma.building.find_unique(
        where={"id": in_progress.buildingId}
    )
    
    if not building:
        return
    
    # 도시 정보로 생산력 계산
    # 여기서는 임의의 값(20)을 사용, 실제로는 도시의 생산력을 계산해야 함
    production_points = 20
    
    # 건설 상태 확인 - 턴당 1의 진행도, buildTime에 도달하면 완료
    # Prisma 스키마에 progressPoints 필드가 없다면 추가 필요
    current_progress = in_progress.progressPoints if hasattr(in_progress, "progressPoints") else 0
    new_progress = current_progress + production_points
    
    # 건설 완료 여부 확인
    if new_progress >= building.buildTime:
        # 건설 완료 처리
        await prisma.playerbuilding.update(
            where={"id": in_progress.id},
            data={
                "status": "completed",
                "progressPoints": building.buildTime,
                "completedAt": prisma.datetime.now()
            }
        )
        
        # 건설 큐에서 다음 건물 가져와서 건설 시작
        queue_entry = await prisma.buildqueue.find_first(
            where={
                "cityId": city_id,
                "queueOrder": 1
            }
        )
        
        if queue_entry:
            # 큐에서 첫 번째 건물 가져와서 건설 시작
            next_building_id = queue_entry.buildingId
            
            # 도시 정보 조회
            city = await prisma.city.find_unique(
                where={"id": city_id}
            )
            
            if not city:
                return
            
            # 건설 시작
            await prisma.playerbuilding.create(
                data={
                    "cityId": city_id,
                    "buildingId": next_building_id,
                    "gameCivId": city.gameCivId,
                    "status": "in_progress",
                    "progressPoints": 0,
                    "startedAt": prisma.datetime.now()
                }
            )
            
            # 큐에서 제거
            await prisma.buildqueue.delete(
                where={"id": queue_entry.id}
            )
            
            # 나머지 큐 재정렬
            await prisma.buildqueue.update_many(
                where={
                    "cityId": city_id,
                    "queueOrder": {
                        "gt": 1
                    }
                },
                data={
                    "queueOrder": {
                        "decrement": 1
                    }
                }
            )
    else:
        # 건설 진행 중인 경우 진행도만 업데이트
        await prisma.playerbuilding.update(
            where={"id": in_progress.id},
            data={
                "progressPoints": new_progress
            }
        )

@router.get("/games")
async def get_games():
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                # 실제 연결 오류인 경우에만 오류 반환
                if "Could not connect" in str(e):
                    return JSONResponse(
                        status_code=500,
                        content={
                            "success": False,
                            "data": None,
                            "error": f"데이터베이스 연결 오류: {str(e)}"
                        }
                    )
        
        games = await prisma.game.find_many()
        return {
            "success": True,
            "data": games,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"서버 오류: {str(e)}"
        }

@router.get("/games/{game_id}")
async def get_game(game_id: int):
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                # 실제 연결 오류인 경우에만 오류 반환
                if "Could not connect" in str(e):
                    return JSONResponse(
                        status_code=500,
                        content={
                            "success": False,
                            "data": None,
                            "error": f"데이터베이스 연결 오류: {str(e)}"
                        }
                    )
        
        game = await prisma.game.find_unique(
            where={
                'id': game_id
            }
        )
        
        if not game:
            return {
                "success": False,
                "data": None,
                "error": f"게임 ID {game_id}에 해당하는 게임을 찾을 수 없습니다."
            }
            
        return {
            "success": True,
            "data": game,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"서버 오류: {str(e)}"
        }

async def get_civ_data(civ_id: int) -> Dict[str, Any]:
    """특정 문명의 상세 데이터를 수집합니다."""
    # 문명 기본 정보
    civ = await prisma.gameciv.find_unique(
        where={"id": civ_id}
    )
    
    if not civ:
        return {}
    
    # 문명 도시 정보
    cities = await prisma.city.find_many(
        where={"gameCivId": civ_id}
    )
    
    city_data = []
    for city in cities:
        # 도시 내 건물 정보
        buildings = await prisma.playerbuilding.find_many(
            where={
                "cityId": city.id,
                "status": "completed"
            },
            include={
                "building": True
            }
        )
        
        # 현재 건설 중인 건물
        in_progress_building = await prisma.playerbuilding.find_first(
            where={
                "cityId": city.id,
                "status": "in_progress"
            },
            include={
                "building": True
            }
        )
        
        # 건설 큐
        build_queue = await prisma.buildqueue.find_many(
            where={"cityId": city.id}
        )
        
        sorted_queue = sorted(build_queue, key=lambda x: x.queueOrder)
        
        city_data.append({
            "id": city.id,
            "name": city.name,
            "population": city.population,
            "buildings": [{"id": b.buildingId, "name": b.building.name, "type": b.building.category} for b in buildings],
            "in_progress": {
                "building": in_progress_building.building.name if in_progress_building else None,
                "progress": in_progress_building.progressPoints if in_progress_building and hasattr(in_progress_building, "progressPoints") else None,
                "required": in_progress_building.building.buildTime if in_progress_building else None
            } if in_progress_building else None,
            "queue": [{"id": q.buildingId} for q in sorted_queue]
        })
    
    # 연구 상태
    completed_techs = await prisma.gamecivtechnology.find_many(
        where={
            "gameCivId": civ_id,
            "status": "completed"
        },
        include={
            "technology": True
        }
    )
    
    in_progress_tech = await prisma.gamecivtechnology.find_first(
        where={
            "gameCivId": civ_id,
            "status": "in_progress"
        },
        include={
            "technology": True
        }
    )
    
    research_queue = await prisma.researchqueue.find_many(
        where={"gameCivId": civ_id}
    )
    
    sorted_research_queue = sorted(research_queue, key=lambda x: x.queuePosition)
    
    # 최종 데이터 구성
    civ_data = {
        "id": civ.id,
        "name": civ.name,
        "cities": city_data,
        "research": {
            "completed": [{"id": t.techId, "name": t.technology.name, "era": t.technology.era} for t in completed_techs],
            "in_progress": {
                "id": in_progress_tech.techId,
                "name": in_progress_tech.technology.name,
                "progress": in_progress_tech.progressPoints,
                "required": in_progress_tech.technology.researchCost
            } if in_progress_tech else None,
            "queue": [{"id": r.techId} for r in sorted_research_queue]
        },
        "resources": {
            "gold": civ.gold,
            "science": civ.science
        }
    }
    
    return civ_data

async def get_ai_decisions(civ_data: Dict[str, Any], game_state: Dict[str, Any], turn: int) -> Dict[str, Any]:
    """LLM API를 호출하여 AI 문명의 결정사항을 가져옵니다."""
    # LLM API 엔드포인트 설정
    api_key = os.getenv("LLM_API_KEY", "YOUR_LLM_API_KEY")
    api_url = os.getenv("LLM_API_URL", "https://api.example.com/v1/completion")
    
    # 문맥 구성
    prompt = f"""
문명 게임에서 당신은 다음 문명의 AI 플레이어 역할을 맡게 됩니다:

현재 턴: {turn}
문명 이름: {civ_data.get('name')}

도시:
{json.dumps(civ_data.get('cities', []), indent=2, ensure_ascii=False)}

연구 상태:
{json.dumps(civ_data.get('research', {}), indent=2, ensure_ascii=False)}

자원:
{json.dumps(civ_data.get('resources', {}), indent=2, ensure_ascii=False)}

게임 상황:
{json.dumps(game_state, indent=2, ensure_ascii=False)}

이번 턴에 당신의 문명이 취해야 할 행동을 결정하세요:
1. 각 도시별로 건설할 건물 또는 생산할 유닛
2. 연구할 기술
3. 기타 중요한 결정사항

다음 JSON 형식으로 답변해주세요:
{{
  "cities": [
    {{
      "city_id": 도시ID,
      "build": {{
        "type": "building" 또는 "unit",
        "id": 건물ID 또는 유닛ID
      }}
    }}
  ],
  "research": {{
    "tech_id": 연구할 기술ID
  }}
}}
"""

    try:
        # 실제 환경에서는 HTTP 요청을 통해 LLM API 호출
        # 현재 개발 환경에서는 임의의 결정 생성
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         api_url,
        #         headers={"Authorization": f"Bearer {api_key}"},
        #         json={"prompt": prompt, "max_tokens": 1000}
        #     )
        #     result = response.json()
        #     ai_decisions = json.loads(result["choices"][0]["text"])
        #     return ai_decisions
        
        # 개발 환경용 임시 결정 (랜덤 생성)
        return generate_mock_ai_decisions(civ_data)
        
    except Exception as e:
        print(f"LLM API 호출 오류: {str(e)}")
        # 오류 발생 시 기본적인 결정 반환
        return {
            "cities": [],
            "research": None
        }

def generate_mock_ai_decisions(civ_data: Dict[str, Any]) -> Dict[str, Any]:
    """개발 환경에서 테스트를 위한 모의 AI 결정을 생성합니다."""
    decisions = {
        "cities": [],
        "research": None
    }
    
    # 도시별 결정
    for city in civ_data.get("cities", []):
        # 이미 건설 중인 건물이 있으면 패스
        if city.get("in_progress"):
            continue
            
        # 랜덤 건물 ID (실제로는 유효한 건물 ID를 사용해야 함)
        building_id = random.randint(1, 10)
        
        decisions["cities"].append({
            "city_id": city.get("id"),
            "build": {
                "type": "building",  # 유닛 생산 기능 추가 시 "unit"도 가능
                "id": building_id
            }
        })
    
    # 연구 결정 (현재 연구 중이 아닌 경우만)
    if not civ_data.get("research", {}).get("in_progress"):
        # 랜덤 기술 ID (실제로는 유효한 기술 ID를 사용해야 함)
        tech_id = random.randint(1, 15)
        decisions["research"] = {"tech_id": tech_id}
    
    return decisions

async def apply_ai_decisions(civ_id: int, decisions: Dict[str, Any]):
    """AI 결정사항을 게임에 적용합니다."""
    # 도시별 결정 적용
    for city_decision in decisions.get("cities", []):
        city_id = city_decision.get("city_id")
        build_data = city_decision.get("build")
        
        if not city_id or not build_data:
            continue
        
        # 현재 건설 중인 건물이 있는지 확인
        in_progress = await prisma.playerbuilding.find_first(
            where={
                "cityId": city_id,
                "status": "in_progress"
            }
        )
        
        # 이미 건설 중인 건물이 있으면 큐에 추가
        if in_progress:
            if build_data.get("type") == "building":
                # 건설 큐에 추가
                current_queue = await prisma.buildqueue.find_many(
                    where={"cityId": city_id}
                )
                
                next_position = 1
                if current_queue:
                    next_position = max(entry.queueOrder for entry in current_queue) + 1
                
                await prisma.buildqueue.create(
                    data={
                        "cityId": city_id,
                        "buildingId": build_data.get("id"),
                        "queueOrder": next_position,
                        "addedAt": prisma.datetime.now()
                    }
                )
            # elif build_data.get("type") == "unit":
                # TODO: 유닛 생산 큐 구현
        else:
            # 건설 중인 건물이 없으면 바로 건설 시작
            if build_data.get("type") == "building":
                # 도시 정보 조회
                city = await prisma.city.find_unique(
                    where={"id": city_id}
                )
                
                if not city:
                    continue
                
                # 건설 시작
                await prisma.playerbuilding.create(
                    data={
                        "cityId": city_id,
                        "buildingId": build_data.get("id"),
                        "gameCivId": civ_id,
                        "status": "in_progress",
                        "progressPoints": 0,
                        "startedAt": prisma.datetime.now()
                    }
                )
            # elif build_data.get("type") == "unit":
                # TODO: 유닛 생산 구현
    
    # 연구 결정 적용
    research_decision = decisions.get("research")
    if research_decision:
        tech_id = research_decision.get("tech_id")
        
        # 현재 연구 중인 기술이 있는지 확인
        in_progress = await prisma.gamecivtechnology.find_first(
            where={
                "gameCivId": civ_id,
                "status": "in_progress"
            }
        )
        
        # 이미 연구 중인 기술이 있으면 큐에 추가
        if in_progress:
            current_queue = await prisma.researchqueue.find_many(
                where={"gameCivId": civ_id}
            )
            
            next_position = 1
            if current_queue:
                next_position = max(entry.queuePosition for entry in current_queue) + 1
            
            await prisma.researchqueue.create(
                data={
                    "gameCivId": civ_id,
                    "techId": tech_id,
                    "queuePosition": next_position,
                    "addedAt": prisma.datetime.now()
                }
            )
        else:
            # 연구 중인 기술이 없으면 바로 연구 시작
            existing_record = await prisma.gamecivtechnology.find_first(
                where={
                    "gameCivId": civ_id,
                    "techId": tech_id
                }
            )
            
            if existing_record:
                # 기존 레코드 업데이트
                await prisma.gamecivtechnology.update(
                    where={"id": existing_record.id},
                    data={
                        "status": "in_progress",
                        "progressPoints": 0,
                        "startedAt": prisma.datetime.now()
                    }
                )
            else:
                # 새 레코드 생성
                await prisma.gamecivtechnology.create(
                    data={
                        "gameCivId": civ_id,
                        "techId": tech_id,
                        "status": "in_progress",
                        "progressPoints": 0,
                        "startedAt": prisma.datetime.now()
                    }
                )

@router.get("/{game_id}/player-status", summary="플레이어 상태 조회", response_description="플레이어의 연구, 유닛, 건물 상태 반환")
async def get_player_status(game_id: int, turn: Optional[int] = Query(None, description="조회할 턴 번호 (기본: 현재 턴)")):
    """
    플레이어의 현재 게임 상태 (연구, 유닛, 건물)를 조회합니다.
    특정 턴을 지정하지 않으면 현재 턴 기준으로 데이터를 반환합니다.
    """
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                # 실제 연결 오류인 경우에만 오류 반환
                if "Could not connect" in str(e):
                    return JSONResponse(
                        status_code=500,
                        content={
                            "success": False,
                            "data": None,
                            "error": f"데이터베이스 연결 오류: {str(e)}"
                        }
                    )
        
        # 게임 존재 확인
        game = await prisma.game.find_unique(
            where={"id": game_id}
        )
        
        if not game:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "data": None,
                    "error": f"게임 ID {game_id}에 해당하는 게임을 찾을 수 없습니다."
                }
            )
        
        # 턴이 지정되지 않은 경우 현재 턴 사용
        current_turn = turn if turn is not None else game.currentTurn
        
        # 플레이어 문명 찾기
        player_civ = await prisma.gameciv.find_first(
            where={
                "gameId": game_id,
                "isPlayer": True
            }
        )
        
        if not player_civ:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "data": None,
                    "error": "플레이어 문명을 찾을 수 없습니다."
                }
            )
        
        # 지정된 턴이 현재 턴보다 크면 오류 반환
        if current_turn > game.currentTurn:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "data": None,
                    "error": f"지정한 턴({current_turn})이 현재 턴({game.currentTurn})보다 클 수 없습니다."
                }
            )
        
        # 1. 연구 정보 조회
        # 완료된 연구
        completed_techs = await prisma.gamecivtechnology.find_many(
            where={
                "gameCivId": player_civ.id,
                "status": "completed"
            },
            include={
                "technology": True
            }
        )
        
        # 진행 중인 연구
        in_progress_tech = await prisma.gamecivtechnology.find_first(
            where={
                "gameCivId": player_civ.id,
                "status": "in_progress"
            },
            include={
                "technology": True
            }
        )
        
        # 연구 큐
        research_queue = await prisma.researchqueue.find_many(
            where={"gameCivId": player_civ.id},
            include={
                "technology": True
            },
            order_by={
                "queuePosition": "asc"
            }
        )
        
        # 2. 유닛 정보 조회
        units = await prisma.unit.find_many(
            where={
                "gameCivId": player_civ.id
            },
            include={
                "unitType": True
            }
        )
        
        # 3. 도시 및 건물 정보 조회
        cities = await prisma.city.find_many(
            where={
                "gameCivId": player_civ.id
            }
        )
        
        cities_data = []
        for city in cities:
            # 완료된 건물
            completed_buildings = await prisma.playerbuilding.find_many(
                where={
                    "cityId": city.id,
                    "status": "completed"
                },
                include={
                    "building": True
                }
            )
            
            # 진행 중인 건물
            in_progress_building = await prisma.playerbuilding.find_first(
                where={
                    "cityId": city.id,
                    "status": "in_progress"
                },
                include={
                    "building": True
                }
            )
            
            # 건설 큐
            build_queue = await prisma.buildqueue.find_many(
                where={"cityId": city.id},
                include={
                    "building": True
                },
                order_by={
                    "queueOrder": "asc"
                }
            )
            
            cities_data.append({
                "id": city.id,
                "name": city.name,
                "population": city.population,
                "location": {"q": city.q, "r": city.r},
                "buildings": [
                    {
                        "id": building.buildingId,
                        "name": building.building.name,
                        "category": building.building.category,
                        "effects": building.building.effects
                    }
                    for building in completed_buildings
                ],
                "in_progress": {
                    "id": in_progress_building.buildingId,
                    "name": in_progress_building.building.name,
                    "progress": in_progress_building.progressPoints,
                    "required": in_progress_building.building.buildTime
                } if in_progress_building else None,
                "queue": [
                    {
                        "id": queue_item.buildingId,
                        "name": queue_item.building.name,
                        "position": queue_item.queueOrder
                    }
                    for queue_item in build_queue
                ]
            })
        
        # 4. 리소스 정보
        resources = {
            "gold": player_civ.gold,
            "science": player_civ.science,
            "food": player_civ.food if hasattr(player_civ, "food") else 0,
            "production": player_civ.production if hasattr(player_civ, "production") else 0
        }
        
        # 최종 응답 데이터 구성
        response_data = {
            "game_id": game_id,
            "turn": current_turn,
            "player_civ": {
                "id": player_civ.id,
                "name": player_civ.name,
                "resources": resources,
                "research": {
                    "completed": [
                        {
                            "id": tech.techId,
                            "name": tech.technology.name,
                            "era": tech.technology.era,
                            "completed_at": tech.completedAt.isoformat() if tech.completedAt else None
                        }
                        for tech in completed_techs
                    ],
                    "in_progress": {
                        "id": in_progress_tech.techId,
                        "name": in_progress_tech.technology.name,
                        "progress": in_progress_tech.progressPoints,
                        "required": in_progress_tech.technology.researchCost
                    } if in_progress_tech else None,
                    "queue": [
                        {
                            "id": item.techId,
                            "name": item.technology.name,
                            "position": item.queuePosition
                        }
                        for item in research_queue
                    ]
                },
                "units": [
                    {
                        "id": unit.id,
                        "type_id": unit.unitTypeId,
                        "type_name": unit.unitType.name,
                        "category": unit.unitType.category,
                        "location": {"q": unit.q, "r": unit.r},
                        "hp": unit.hp,
                        "moves_left": unit.movesLeft
                    }
                    for unit in units
                ],
                "cities": cities_data
            }
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": response_data,
                "error": None
            }
        )
        
    except Exception as e:
        print(f"Error in get_player_status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": f"서버 오류: {str(e)}"
            }
        )
