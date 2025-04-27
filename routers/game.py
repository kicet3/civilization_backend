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
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

class GameSummary(BaseModel):
    """게임 종료 시 저장할 요약 데이터 모델"""
    # 게임 기본 정보
    gameId: str
    userId: Optional[str] = None
    turn: int
    year: Optional[int] = None
    difficulty: Optional[str] = None
    mapType: Optional[str] = None
    gameMode: Optional[str] = None
    victoryType: Optional[str] = None
    
    # 타임스탬프
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    totalPlayTime: Optional[int] = None
    
    # 문명 상태 정보
    civilizationId: Optional[int] = None
    civilizationName: Optional[str] = None
    leaderName: Optional[str] = None
    
    # 자원 현황
    resources: Dict[str, int] = {}
    
    # 도시 정보
    cities: List[Dict[str, Any]] = []
    totalCities: int = 0
    capitalCity: Optional[Dict[str, Any]] = None
    capturedCities: int = 0
    foundedCities: int = 0
    
    # 유닛 정보
    units: List[Dict[str, Any]] = []
    totalUnits: int = 0
    militaryUnits: int = 0
    civilianUnits: int = 0
    unitsLost: int = 0
    unitsKilled: int = 0
    
    # 기술 및 연구 정보
    completedTechnologies: List[Dict[str, Any]] = []
    currentResearch: Optional[Dict[str, Any]] = None
    researchProgress: Optional[int] = None
    researchQueue: List[Dict[str, Any]] = []
    totalTechsResearched: int = 0
    techEra: Optional[str] = None
    selectedTechTrees: Dict[str, str] = {}
    
    # 외교 정보
    diplomacyStates: List[Dict[str, Any]] = []
    wars: int = 0
    alliances: int = 0
    trades: int = 0
    
    # 전투 및 전략 정보
    battles: List[Dict[str, Any]] = []
    territoryCaptured: int = 0
    territoryLost: int = 0
    successfulDefenses: int = 0
    successfulAttacks: int = 0
    
    # 이벤트 및 액션 로그
    events: List[Dict[str, Any]] = []
    actionCounts: Dict[str, int] = {}
    
    # 맵 상태 정보
    exploredTiles: int = 0
    visibleTiles: int = 0
    unexploredTiles: int = 0
    resourceLocations: List[Dict[str, Any]] = []
    
    # 성과 및 점수
    totalScore: int = 0
    scoreComponents: Dict[str, int] = {}
    achievements: List[str] = []
    milestones: List[Dict[str, Any]] = []

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
    user_name: Optional[str] = Query(None, description="사용자 이름"),
    game_summary: Optional[GameSummary] = None
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
            # 1. 도시별 자원 수집 업데이트
            player_cities = await prisma.city.find_many(
                where={
                    "gameCivId": player_civ_id
                }
            )
            
            for city in player_cities:
                await update_city_resources(city.id)
            
            # 2. 연구 진행 상태 업데이트
            await update_research_progress(player_civ_id)
            
            # 3. 각 도시별 건물 건설 및 유닛 생산 업데이트
            for city in player_cities:
                await update_building_construction(city.id)
                await update_unit_production(city.id, next_turn_number)
        
        # AI 문명들의 행동 결정 및 처리
        for ai_civ_id in ai_civ_ids:
            # 자원 수집 업데이트
            ai_cities = await prisma.city.find_many(
                where={
                    "gameCivId": ai_civ_id
                }
            )
            
            for city in ai_cities:
                await update_city_resources(city.id)
            
            # 해당 AI 문명의 정보 수집
            ai_civ = await get_civ_data(ai_civ_id)
            
            # LLM API 호출하여 AI 문명의 행동 결정
            ai_decisions = await get_ai_decisions(ai_civ, current_state.stateData, next_turn_number)
            
            # AI 결정사항 적용
            await apply_ai_decisions(game_id, ai_civ_id, ai_decisions)
            
            # AI 문명 도시들의 생산 업데이트
            for city in ai_cities:
                await update_building_construction(city.id)
                await update_unit_production(city.id, next_turn_number)
        
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
    
        # 게임 요약 데이터가 제공된 경우 저장
        if game_summary:
            # 게임 ID 설정 (URL 파라미터 우선)
            game_summary.gameId = game_id
            # 턴 번호 설정
            game_summary.turn = next_turn_number
            # 게임 요약 정보 저장
            await save_game_summary(game_summary)
        else:
            # 게임 요약 데이터가 없는 경우 자동으로 수집
            await collect_and_save_game_summary(game.id, next_turn_number)
    
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
    # 문명 데이터 조회
    civ_data = await prisma.gameciv.find_unique(
        where={"id": game_civ_id}
    )
    
    if not civ_data:
        return
    
    # 과학 포인트 사용
    science_points = civ_data.science
    
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
    city = await prisma.city.find_unique(
        where={"id": city_id}
    )
    
    if not city:
        return
    
    # 생산력 사용
    production_points = city.production
    
    # 건설 상태 확인 - 생산력에 따라 진행도 증가
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

async def generate_mock_ai_decisions(civ_data: Dict[str, Any]):
    """
    AI의 의사결정을 모의로 생성합니다.
    """
    decisions = {
        "cities": [],
        "research": None
    }
    
    # 각 도시별 의사결정 생성
    for city in civ_data.get("cities", []):
        city_id = city.get("id")
        
        # 이미 건설 중인 건물이 있는지 확인
        building_in_progress = any(building.get("status") == "in_progress" for building in city.get("buildings", []))
        
        # 생산 큐 확인
        production_in_progress = city.get("production_queue") and len(city.get("production_queue")) > 0
        
        # 건설이나 생산 중인 항목이 있으면 스킵
        if building_in_progress or production_in_progress:
            continue
            
        # 건설할 건물 또는 생산할 유닛 선택 (간단히 랜덤으로 결정)
        build_choice = random.choice(["building", "unit"])
        
        if build_choice == "building":
            # 건물 선택 로직
            available_buildings = []
            
            # 연구 완료된 기술 기반 건설 가능 건물 조회
            completed_techs = [tech.get("id") for tech in civ_data.get("research", {}).get("completed_techs", [])]
            
            try:
                all_buildings = await prisma.building.find_many(
                    where={
                        "OR": [
                            {"prerequisiteTechId": {"in": completed_techs}},
                            {"prerequisiteTechId": None}
                        ]
                    }
                )
                
                # 이미 완료된 건물 제외
                completed_building_ids = [
                    building.get("id") 
                    for building in city.get("buildings", []) 
                    if building.get("status") == "completed"
                ]
                
                available_buildings = [
                    building for building in all_buildings 
                    if building.id not in completed_building_ids
                ]
                
                # 건설 큐에 있는 건물 제외
                queued_building_ids = [
                    entry.get("buildingId") for entry in city.get("build_queue", [])
                ]
                
                available_buildings = [
                    building for building in available_buildings 
                    if building.id not in queued_building_ids
                ]
                
            except Exception as e:
                print(f"건물 조회 오류: {e}")
                available_buildings = []
            
            if available_buildings:
                # 간단히 랜덤으로 건물 선택
                selected_building = random.choice(available_buildings)
                
                city_decision = {
                    "city_id": city_id,
                    "build": {
                        "type": "building",
                        "id": selected_building.id,
                        "name": selected_building.name
                    }
                }
                
                decisions["cities"].append(city_decision)
        else:
            # 유닛 선택 로직
            available_units = []
            
            # 연구 완료된 기술 기반 생산 가능 유닛 조회
            completed_techs = [tech.get("id") for tech in civ_data.get("research", {}).get("completed_techs", [])]
            
            try:
                all_units = await prisma.unittype.find_many(
                    where={
                        "OR": [
                            {"prerequisiteTechId": {"in": completed_techs}},
                            {"prerequisiteTechId": None}
                        ]
                    }
                )
                
                available_units = all_units
                
            except Exception as e:
                print(f"유닛 조회 오류: {e}")
                available_units = []
            
            if available_units:
                # 간단히 랜덤으로 유닛 선택
                selected_unit = random.choice(available_units)
                
                city_decision = {
                    "city_id": city_id,
                    "build": {
                        "type": "unit",
                        "id": selected_unit.id,
                        "name": selected_unit.name
                    }
                }
                
                decisions["cities"].append(city_decision)
    
    # 연구 의사결정 - 간단히 랜덤으로 선택
    try:
        # 이미 연구 중인 기술이 있는지 확인
        current_research = civ_data.get("research", {}).get("current_research")
        
        if not current_research:
            # 완료된 기술과 현재 연구 중인 기술 제외하고 선택
            completed_tech_ids = [tech.get("id") for tech in civ_data.get("research", {}).get("completed_techs", [])]
            queued_tech_ids = [entry.get("technologyId") for entry in civ_data.get("research", {}).get("research_queue", [])]
            excluded_tech_ids = completed_tech_ids + queued_tech_ids
            
            available_techs = await prisma.technology.find_many(
                where={
                    "id": {"not": {"in": excluded_tech_ids}}
                }
            )
            
            if available_techs:
                # 기술 트리를 고려한 선택 (여기서는 간단히 랜덤으로 선택)
                selected_tech = random.choice(available_techs)
                
                decisions["research"] = {
                    "tech_id": selected_tech.id,
                    "name": selected_tech.name
                }
    
    except Exception as e:
        print(f"연구 의사결정 오류: {e}")
    
    return decisions

async def apply_ai_decisions(game_id: str, civ_id: str, decisions: Dict[str, Any]):
    """AI의 의사결정을 게임 상태에 적용합니다."""
    
    # 도시별 결정 적용
    for city_decision in decisions.get("cities", []):
        city_id = city_decision.get("city_id")
        build_info = city_decision.get("build")
        
        if not city_id or not build_info:
            continue
        
        try:
            # 도시 정보 조회
            city = await prisma.city.find_unique(
                where={"id": city_id},
                include={
                    "buildings": True
                }
            )
            
            if not city:
                print(f"도시를 찾을 수 없음: {city_id}")
                continue
            
            # 건물 건설 또는 유닛 생산 로직
            build_type = build_info.get("type")
            
            if build_type == "building":
                building_id = build_info.get("id")
                
                # 이미 건설 중인 건물이 있는지 확인
                in_progress_building = await prisma.citybuilding.find_first(
                    where={
                        "cityId": city_id,
                        "status": "in_progress"
                    }
                )
                
                if in_progress_building:
                    # 건설 큐에 추가
                    await prisma.buildqueue.create(
                        data={
                            "cityId": city_id,
                            "buildingId": building_id
                        }
                    )
                else:
                    # 즉시 건설 시작
                    building = await prisma.building.find_unique(
                        where={"id": building_id}
                    )
                    
                    if building:
                        turns_remaining = building.turns_to_build
                        
                        await prisma.citybuilding.create(
                            data={
                                "cityId": city_id,
                                "buildingId": building_id,
                                "status": "in_progress",
                                "turns_remaining": turns_remaining
                            }
                        )
            
            elif build_type == "unit":
                unit_id = build_info.get("id")
                
                # 이미 생산 중인 유닛이 있는지 확인
                in_progress_production = await prisma.productionqueue.find_first(
                    where={
                        "cityId": city_id,
                        "status": "in_progress"
                    }
                )
                
                if in_progress_production:
                    # 생산 큐에 추가 (다음 순서)
                    next_order = 2  # 기본적으로 큐의 두 번째 위치
                    
                    # 현재 큐에서 가장 높은 순서 확인
                    latest_queue_item = await prisma.productionqueue.find_first(
                        where={"cityId": city_id},
                        order={"queueOrder": "desc"}
                    )
                    
                    if latest_queue_item:
                        next_order = latest_queue_item.queueOrder + 1
                    
                    await prisma.productionqueue.create(
                        data={
                            "cityId": city_id,
                            "unitTypeId": unit_id,
                            "queueOrder": next_order,
                            "status": "queued"
                        }
                    )
                else:
                    # 즉시 생산 시작
                    unit_type = await prisma.unittype.find_unique(
                        where={"id": unit_id}
                    )
                    
                    if unit_type:
                        turns_remaining = unit_type.turns_to_build
                        
                        await prisma.productionqueue.create(
                            data={
                                "cityId": city_id,
                                "unitTypeId": unit_id,
                                "turns_remaining": turns_remaining,
                                "status": "in_progress",
                                "queueOrder": 1
                            }
                        )
        
        except Exception as e:
            print(f"도시 결정 적용 오류: {e}")
    
    # 연구 결정 적용
    research_decision = decisions.get("research")
    
    if research_decision:
        tech_id = research_decision.get("tech_id")
        
        if tech_id:
            try:
                # 현재 연구 중인 기술 확인
                civ_data = await prisma.civilization.find_unique(
                    where={"id": civ_id},
                    include={
                        "research_status": {
                            "include": {
                                "current_research": True
                            }
                        }
                    }
                )
                
                if civ_data and civ_data.research_status:
                    research_status_id = civ_data.research_status.id
                    current_research = civ_data.research_status.current_research
                    
                    if current_research:
                        # 이미 연구 중인 기술이 있으면 큐에 추가
                        await prisma.researchqueue.create(
                            data={
                                "researchStatusId": research_status_id,
                                "technologyId": tech_id
                            }
                        )
                    else:
                        # 즉시 연구 시작
                        technology = await prisma.technology.find_unique(
                            where={"id": tech_id}
                        )
                        
                        if technology:
                            turns_remaining = technology.turns_to_research
                            
                            await prisma.researchstatus.update(
                                where={"id": research_status_id},
                                data={
                                    "currentResearchId": tech_id,
                                    "current_research_turns_remaining": turns_remaining
                                }
                            )
            
            except Exception as e:
                print(f"연구 결정 적용 오류: {e}")

async def update_unit_production(city_id: int, current_turn: int):
    """도시의 유닛 생산 상태를 업데이트합니다."""
    # 생산 큐에서 첫 번째 항목 찾기
    current_production = await prisma.productionqueue.find_first(
        where={
            "cityId": city_id,
            "queueOrder": 1,
            "itemType": "unit"
        }
    )
    
    if not current_production:
        # 생산 중인 유닛이 없음
        return
    
    # 도시 정보로 생산력 계산
    city = await prisma.city.find_unique(
        where={"id": city_id}
    )
    
    if not city:
        return
    
    # 유닛 타입 정보 조회
    unit_type = await prisma.unittype.find_unique(
        where={"id": current_production.itemId}
    )
    
    if not unit_type:
        return
    
    # 생산력에 따른 턴 감소 계산
    # 도시의 생산력이 높을수록 더 빠르게 생산됨
    production_modifier = max(1, city.production / 8)  # 생산력 8당 1턴 감소
    turns_reduction = max(1, int(production_modifier))
    new_turns_left = current_production.turnsLeft - turns_reduction
    
    # 생산 완료 여부 확인
    if new_turns_left <= 0:
        # 유닛 생성 (도시 위치에 배치)
        new_unit = await prisma.gameunit.create(
            data={
                "q": city.q,
                "r": city.r,
                "hp": 100,  # 기본 체력
                "moved": False,
                "createdTurn": current_turn,
                "gameCivId": city.gameCivId,
                "unitTypeId": unit_type.id
            }
        )
        
        # 생산 큐에서 제거
        await prisma.productionqueue.delete(
            where={"id": current_production.id}
        )
        
        # 나머지 큐 재정렬
        await prisma.productionqueue.update_many(
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
        # 남은 턴 업데이트
        await prisma.productionqueue.update(
            where={"id": current_production.id},
            data={
                "turnsLeft": new_turns_left
            }
        )

# 새로운 함수: 도시별 자원 수집 업데이트
async def update_city_resources(city_id: int):
    """도시별 자원(식량, 생산력, 골드, 과학) 수집을 업데이트합니다."""
    # 도시 정보 조회
    city = await prisma.city.find_unique(
        where={"id": city_id},
        include={
            "gameCiv": True
        }
    )
    
    if not city:
        return
    
    # 기본 자원 수확량 (도시당)
    food_income = 15
    production_income = 8
    gold_income = 20
    science_income = 6
    
    # 도시 내 건물에 따른 보너스 계산
    buildings = await prisma.playerbuilding.find_many(
        where={
            "cityId": city.id,
            "status": "completed"
        },
        include={
            "building": True
        }
    )
    
    for building in buildings:
        # 건물 유형에 따른 보너스 적용
        if building.building.category == "Science":
            if building.building.name == "도서관":
                science_income += 7
        elif building.building.category == "Production":
            if building.building.name == "작업장":
                production_income += 3
        elif building.building.category == "Trade":
            if building.building.name == "시장":
                gold_income += 8
    
    # 타일 자원에 따른 보너스 계산
    nearby_tiles = await prisma.maptile.find_many(
        where={
            "gameId": city.gameCiv.gameId,
            "OR": [
                # 도시 좌표와 일치
                {"q": city.q, "r": city.r},
                # 인접한 6개 hexagon 좌표
                {"q": city.q, "r": city.r - 1},     # 상단
                {"q": city.q + 1, "r": city.r - 1}, # 우상단
                {"q": city.q + 1, "r": city.r},     # 우하단
                {"q": city.q, "r": city.r + 1},     # 하단
                {"q": city.q - 1, "r": city.r + 1}, # 좌하단
                {"q": city.q - 1, "r": city.r}      # 좌상단
            ]
        }
    )
    
    for tile in nearby_tiles:
        if tile.resource == "Food":
            food_income += 4  # 농장 +4 식량
        elif tile.resource == "Production":
            production_income += 5  # 광산 +5 생산력
        elif tile.resource == "Gold":
            gold_income += 5  # 금광 +5 골드
        elif tile.resource == "Science":
            science_income += 3  # 자연 탐사지 +3 과학
    
    # 도시 자원 업데이트
    await prisma.city.update(
        where={"id": city.id},
        data={
            "food": food_income,
            "production": production_income
        }
    )
    
    # 문명 자원 업데이트
    await prisma.gameciv.update(
        where={"id": city.gameCivId},
        data={
            "gold": {"increment": gold_income},
            "science": {"increment": science_income}
        }
    )
    
    return {
        "food": food_income,
        "production": production_income,
        "gold": gold_income,
        "science": science_income
    }

async def save_game_summary(summary: GameSummary):
    """게임 요약 정보를 데이터베이스에 저장"""
    try:
        # 현재 시간 설정
        if not summary.endTime:
            summary.endTime = datetime.now()
        
        # 기존 데이터가 있는지 확인
        existing_summary = await prisma.gamesummary.find_first(
            where={
                "gameId": summary.gameId,
                "turn": summary.turn
            }
        )
        
        # 데이터 변환
        summary_data = {
            "gameId": summary.gameId,
            "userId": summary.userId,
            "turn": summary.turn,
            "year": summary.year,
            "difficulty": summary.difficulty,
            "mapType": summary.mapType,
            "gameMode": summary.gameMode,
            "victoryType": summary.victoryType,
            "startTime": summary.startTime,
            "endTime": summary.endTime,
            "totalPlayTime": summary.totalPlayTime,
            "civilizationId": summary.civilizationId,
            "civilizationName": summary.civilizationName,
            "leaderName": summary.leaderName,
            "resources": json.dumps(summary.resources),
            "cities": json.dumps(summary.cities),
            "totalCities": summary.totalCities,
            "capitalCity": json.dumps(summary.capitalCity) if summary.capitalCity else None,
            "capturedCities": summary.capturedCities,
            "foundedCities": summary.foundedCities,
            "units": json.dumps(summary.units),
            "totalUnits": summary.totalUnits,
            "militaryUnits": summary.militaryUnits,
            "civilianUnits": summary.civilianUnits,
            "unitsLost": summary.unitsLost,
            "unitsKilled": summary.unitsKilled,
            "completedTechnologies": json.dumps(summary.completedTechnologies),
            "currentResearch": json.dumps(summary.currentResearch) if summary.currentResearch else None,
            "researchProgress": summary.researchProgress,
            "researchQueue": json.dumps(summary.researchQueue),
            "totalTechsResearched": summary.totalTechsResearched,
            "techEra": summary.techEra,
            "selectedTechTrees": json.dumps(summary.selectedTechTrees),
            "diplomacyStates": json.dumps(summary.diplomacyStates),
            "wars": summary.wars,
            "alliances": summary.alliances,
            "trades": summary.trades,
            "battles": json.dumps(summary.battles),
            "territoryCaptured": summary.territoryCaptured,
            "territoryLost": summary.territoryLost,
            "successfulDefenses": summary.successfulDefenses,
            "successfulAttacks": summary.successfulAttacks,
            "events": json.dumps(summary.events),
            "actionCounts": json.dumps(summary.actionCounts),
            "exploredTiles": summary.exploredTiles,
            "visibleTiles": summary.visibleTiles,
            "unexploredTiles": summary.unexploredTiles,
            "resourceLocations": json.dumps(summary.resourceLocations),
            "totalScore": summary.totalScore,
            "scoreComponents": json.dumps(summary.scoreComponents),
            "achievements": json.dumps(summary.achievements),
            "milestones": json.dumps(summary.milestones)
        }
        
        if existing_summary:
            # 기존 데이터 업데이트
            await prisma.gamesummary.update(
                where={"id": existing_summary.id},
                data=summary_data
            )
        else:
            # 새 데이터 생성
            await prisma.gamesummary.create(data=summary_data)
            
        return True
    except Exception as e:
        print(f"게임 요약 저장 오류: {str(e)}")
        return False

async def collect_and_save_game_summary(game_id: str, turn: int):
    """게임 데이터를 수집하여 요약 정보 생성 및 저장"""
    try:
        # 게임 정보 조회
        game = await prisma.game.find_unique(
            where={"id": game_id}
        )
        
        if not game:
            return False
            
        # 문명 정보 조회
        player_civ = await prisma.gameciv.find_first(
            where={
                "gameId": game_id,
                "isPlayer": True
            },
            include={
                "civType": True
            }
        )
        
        if not player_civ:
            return False
            
        # 도시 정보 조회
        cities = await prisma.city.find_many(
            where={"gameCivId": player_civ.id}
        )
        
        # 유닛 정보 조회
        units = await prisma.gameunit.find_many(
            where={"gameCivId": player_civ.id},
            include={"unitType": True}
        )
        
        # 연구 정보 조회
        completed_techs = await prisma.gamecivtechnology.find_many(
            where={
                "gameCivId": player_civ.id,
                "status": "completed"
            },
            include={"technology": True}
        )
        
        current_research = await prisma.gamecivtechnology.find_first(
            where={
                "gameCivId": player_civ.id,
                "status": "in_progress"
            },
            include={"technology": True}
        )
        
        research_queue = await prisma.researchqueue.find_many(
            where={"gameCivId": player_civ.id},
            include={"technology": True}
        )
        
        # 맵 정보 조회
        map_tiles = await prisma.maptile.find_many(
            where={"gameId": game_id}
        )
        
        # 기술 트리 선택 정보
        tech_trees = await prisma.treeselection.find_many(
            where={"gameCivId": player_civ.id}
        )
        
        # 요약 정보 생성
        summary = GameSummary(
            gameId=game_id,
            userId=game.userName,
            turn=turn,
            startTime=game.createdAt,
            endTime=datetime.now(),
            totalPlayTime=int((datetime.now() - game.createdAt).total_seconds() / 60),  # 분 단위
            
            civilizationId=player_civ.civTypeId,
            civilizationName=player_civ.civType.name if player_civ.civType else None,
            leaderName=player_civ.civType.leaderName if player_civ.civType else None,
            
            resources={
                "food": player_civ.food if hasattr(player_civ, "food") else 0,
                "production": player_civ.production if hasattr(player_civ, "production") else 0,
                "gold": player_civ.gold if hasattr(player_civ, "gold") else 0,
                "science": player_civ.science if hasattr(player_civ, "science") else 0
            },
            
            cities=[{
                "id": city.id,
                "name": city.name,
                "population": city.population,
                "location": {"q": city.q, "r": city.r}
            } for city in cities],
            
            totalCities=len(cities),
            
            units=[{
                "id": unit.id,
                "type": unit.unitType.category if unit.unitType else "Unknown",
                "name": unit.unitType.name if unit.unitType else "Unknown",
                "location": {"q": unit.q, "r": unit.r},
                "health": unit.hp
            } for unit in units],
            
            totalUnits=len(units),
            militaryUnits=sum(1 for unit in units if unit.unitType and unit.unitType.category != "Civilian"),
            civilianUnits=sum(1 for unit in units if unit.unitType and unit.unitType.category == "Civilian"),
            
            completedTechnologies=[{
                "id": tech.techId,
                "name": tech.technology.name if tech.technology else "Unknown",
                "era": tech.technology.era if tech.technology else "Unknown"
            } for tech in completed_techs],
            
            currentResearch={
                "id": current_research.techId,
                "name": current_research.technology.name,
                "progress": current_research.progressPoints,
                "required": current_research.technology.researchCost
            } if current_research else None,
            
            researchQueue=[{
                "id": item.techId,
                "name": item.technology.name if item.technology else "Unknown",
                "position": item.queuePosition
            } for item in sorted(research_queue, key=lambda x: x.queuePosition)],
            
            totalTechsResearched=len(completed_techs),
            
            selectedTechTrees={
                "mainTree": next((tree.treeType for tree in tech_trees if tree.isMain), None),
                "subTree": next((tree.treeType for tree in tech_trees if not tree.isMain), None)
            },
            
            exploredTiles=len(map_tiles),
            
            # 점수 계산 (간단한 예시)
            totalScore=len(cities) * 100 + len(units) * 20 + len(completed_techs) * 50
        )
        
        # 요약 정보 저장
        await save_game_summary(summary)
        
        return True
    except Exception as e:
        print(f"게임 요약 데이터 수집 오류: {str(e)}")
        return False
