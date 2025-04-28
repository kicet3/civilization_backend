from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Path
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
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter()

from fastapi import Body
class CivilizationInfo(BaseModel):
    id: int
    name: str
    leaderName: Optional[str] = None

class LocationInfo(BaseModel):
    q: int
    r: int
    s: int

class CityInfo(BaseModel):
    id: int
    name: str
    population: int
    location: LocationInfo
    buildings: List[str]

class UnitInfo(BaseModel):
    id: int
    location: LocationInfo
    hp: int
    maxHp: int
    movement: int
    maxMovement: int
    status: str

class ResourceTile(BaseModel):
    resource: str
    location: LocationInfo

class DiplomacyInfo(BaseModel):
    wars: int
    alliances: int
    trades: int

class StatsInfo(BaseModel):
    totalCities: int
    capturedCities: int
    foundedCities: int
    totalUnits: int
    militaryUnits: int
    civilianUnits: int
    unitsLost: int
    unitsKilled: int
    totalTechsResearched: int
    exploredTiles: int
    visibleTiles: int
    unexploredTiles: int
    totalScore: int

class MapStateInfo(BaseModel):
    resourceLocations: List[ResourceTile]

class TileInfo(BaseModel):
    location: LocationInfo
    resource: str
    resourceAmount: int
    terrain: str
    movementCost: int


class TurnNextRequest(BaseModel):
    """턴 진행 요청 모델"""
    achievements : List[str] = []
    actionCounts: Dict[str, int] = {}
    actions:List[str] = []
    capitalCity : CityInfo
    capturedCities:List[CityInfo] = []
    cities : List[CityInfo] = []
    civilianUnits:List[UnitInfo] = []
    civilizationId:int
    civilizationName:str
    currentResearch : List[str] = []
    difficulty : str
    diplomacyStates:List[DiplomacyInfo] = []
    endTime:datetime
    exploredTiles:int
    events:List[str] = []
    foundedCities:List[CityInfo] = []
    leaderName:str
    militaryUnits:List[UnitInfo] = []
    researchProgress:List[str] = []
    researchQueue:List[str] = []
    resources:Dict[str, int] = {}
    resourceLocations:List[ResourceTile] = []
    scoreComponents : Dict[str, int] = {}
    selectedTechTrees : List[str] = []
    startTime:datetime
    successfulAttacks : int
    successfulDefenses :int
    techEra : str
    territoryCaptured : int
    territoryLost: int
    totalCities : int
    totalPlayTime : int
    totalScore : int
    totalTechsResearched : int
    totalUnits : int
    trades : int
    turn : int
    unexploredTiles : int
    units : List[UnitInfo] = []
    unitsKilled : int
    victoryType : str
    unitsLost : int
    visibleTiles : int
    wars : int
    year : int
    tiles : List[TileInfo] = []
    gameId :int

@router.post("/turn/end")
async def end_turn(request: TurnNextRequest = Body(...)):
    """
    프론트엔드에서 보낸 게임 상태를 바탕으로
    - 해당 턴의 정보를 업데이트하고
    - 다음 턴의 게임 상태 데이터를 반환합니다.
    """
    try:
        # 1. 전달받은 게임 상태 파싱
        game_summary = request
        if hasattr(game_summary, 'civilizationId'):
            game_id = str(game_summary.gameId)
            current_turn = game_summary.turn
            next_turn = current_turn + 1
        else:
            logger.error("[turn/end] 유효하지 않은 요청: 필수 필드 부족")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "유효하지 않은 요청: 필수 필드가 없습니다."
                }
            )

        # 2. 프론트에서 전달받은 데이터를 기반으로 DB 업데이트
        # 도시 정보 업데이트
        if hasattr(request, "cities"):
            for city in request.cities:
                await prisma.city.update(
                    where={"id": city.id},
                    data={
                        "name": city.name,
                        "population": city.population,
                        "q": city.location.q if hasattr(city.location, 'q') else None,
                        "r": city.location.r if hasattr(city.location, 'r') else None,
                        # 필요한 경우 food, production 등도 추가
                    }
                )

        # 유닛 정보 업데이트
        if hasattr(request, "units"):
            for unit in request.units:
                await prisma.gameunit.update(
                    where={"id": unit.id},
                    data={
                        "q": unit.location.q if hasattr(unit.location, 'q') else None,
                        "r": unit.location.r if hasattr(unit.location, 'r') else None,
                        "hp": unit.hp,
                        # 필요한 경우 moved, promotionLevel 등도 추가
                    }
                )

        # 자원 정보 업데이트 (문명/플레이어)
        if hasattr(request, "resources"):
            await prisma.gameciv.update(
                where={"id": request.civilizationId},
                data={
                    "gold": request.resources.get("gold", 0),
                    "science": request.resources.get("science", 0),
                    "culture": request.resources.get("culture", 0),
                    # 필요한 경우 추가 자원 필드 업데이트
                }
            )

        # 기타 필요한 정보(연구, 건설 등)도 request 기반으로 확장 가능

        # 3. AI 턴 처리 (기존 로직 유지)
        ai_civs = await prisma.gameciv.find_many(where={"gameId": game_id, "isPlayer": False})
        for ai_civ in ai_civs:
            civ_data = await get_civ_data(ai_civ.id)
            ai_decisions = await generate_mock_ai_decisions(civ_data)
            await apply_ai_decisions(game_id, ai_civ.id, ai_decisions)

        # 4. 새로운 턴 상태 스냅샷 저장 (TurnSnapshot 테이블 사용)
        await collect_and_save_game_summary(game_id, next_turn)

        # 5. 다음 턴의 전체 게임 상태 반환 (TurnSnapshot 테이블에서 최신 상태 조회)
        a= await prisma.turnsnapshot.find_first(where={"gameId": game_id, "turnNumber": next_turn})
        print('게임 상태',a)
        response = {}
        response["message"] = "턴이 정상적으로 종료되었으며, 다음 턴 데이터가 반환됩니다."
        response["success"] = True
        return JSONResponse(content=response)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"턴 종료 처리 중 오류가 발생했습니다: {str(e)}"
            }
        )

class GameSummary(BaseModel):
    """게임 상태 전체를 요약하는 모델"""
    gameId: str
    userId: str
    turn: int
    year: int
    difficulty: str = None
    mapType: str = None
    gameMode: str = None
    victoryType: str = None
    createdAt: datetime = None
    updatedAt: datetime = None
    civilization: dict = None
    resources: dict = None
    cities: list = None
    units: list = None
    technologies: list = None
    diplomacy: dict = None
    stats: dict = None
    mapState: dict = None
    gameStatus: str = "ACTIVE"  # ACTIVE, PAUSED, ENDED

class TurnNextRequest(BaseModel):
    """턴 진행 요청 모델"""
    gameId: str
    turn: int = None
    next_year: int = None
    current_turn: int = None
    era: str = None
    game_summary: GameSummary = None

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
        
        # TurnSnapshot에서 게임 상태 조회 (재화 정보 포함)
        turn_snapshot = await prisma.turnsnapshot.find_first(
            where={
                "gameId": game.id,
                "turnNumber": query_turn
            }
        )
        
        # TurnSnapshot이 없는 경우 기존 TurnSnapshot에서 조회
        if not turn_snapshot:
            # TurnSnapshot이 없는 경우 TurnSnapshot에서 조회
            game_state = await prisma.turnsnapshot.find_first(
                where={
                    "gameId": game.id,
                    "turnNumber": query_turn
                }
            )
            
            if not game_state:
                return {
                    "success": False,
                    "status_code": 404,
                    "message": f"턴 {query_turn}의 게임 상태를 찾을 수 없습니다."
                }
                
            # 플레이어 문명 정보 조회 (재화 데이터용)
            player_civ = await prisma.gameciv.find_first(
                where={
                    "gameId": game.id,
                    "id": game.playerCivId
                }
            )
            
            # 플레이어 도시들의 식량과 생산력 정보 조회
            player_cities = None
            total_food = 0
            total_production = 0
            
            if player_civ:
                player_cities = await prisma.city.find_many(
                    where={
                        "gameCivId": player_civ.id
                    }
                )
                
                if player_cities:
                    for city in player_cities:
                        total_food += city.food
                        total_production += city.production
            
            # 플레이어 재화 정보 추가
            player_resources = {
                "gold": player_civ.gold if player_civ else 0,
                "science": player_civ.science if player_civ else 0,
                "culture": player_civ.culture if player_civ else 0,
                "food": total_food,
                "production": total_production
            }
            
            # 실제 턴 데이터가 state_data에 들어가 있는지 확인하고, 없으면 생성
            if not state_data or not isinstance(state_data, dict) or not state_data.get("cities"):
                # 예시: cities, units, resources 등 실제 턴 데이터 구성
                state_data = {
                    "cities": [city.dict() for city in player_cities] if player_cities else [],
                    "resources": player_resources,
                    # 필요에 따라 units, tiles 등도 추가
                }
            
            # TurnSnapshot에 저장하여 다음에는 더 빠르게 조회할 수 있도록 함
            try:
                await prisma.turnsnapshot.create(
                    data={
                        "gameId": game.id,
                        "turnNumber": query_turn,
                        "stateData": state_data,
                        "playerResources": player_resources,
                        "observedMap": {},  # 기본 빈 맵 정보
                        "civId": game.playerCivId,
                        "diplomacyState": {},
                        "productionState": {},
                        "researchState": {}
                    }
                )
            except Exception as snapshot_error:
                logger.error(f"TurnSnapshot 생성 중 오류: {str(snapshot_error)}")
                # 스냅샷 생성 실패해도 계속 진행
        else:
            # TurnSnapshot에서 데이터 가져오기
            try:
                state_data = getattr(turn_snapshot, 'stateData', None)
            except AttributeError:
                state_data = None
            
            # playerResources가 없는 경우 (스키마 마이그레이션 전 데이터)
            try:
                player_resources = getattr(turn_snapshot, 'playerResources', None)
            except AttributeError:
                # playerResources 속성이 없는 경우
                player_resources = None
            
            # state_data가 없는 경우 TurnSnapshot에서 가져오기
            if not state_data:
                # TurnSnapshot에서 데이터 가져오기
                game_state = await prisma.turnsnapshot.find_first(
                    where={
                        "gameId": game.id,
                        "turnNumber": query_turn
                    }
                )
                
                if game_state:
                    state_data = game_state.stateData
                    
                    # TurnSnapshot 업데이트 시도 - 에러 무시
                    try:
                        await prisma.turnsnapshot.update(
                            where={"id": turn_snapshot.id},
                            data={"stateData": state_data}
                        )
                    except Exception as update_error:
                        logger.error(f"TurnSnapshot stateData 업데이트 중 오류: {str(update_error)}")
            
            # 재화 정보가 없으면 직접 계산
            if not player_resources:
                # 플레이어 문명 정보 조회
                player_civ = await prisma.gameciv.find_first(
                    where={
                        "gameId": game.id,
                        "id": game.playerCivId
                    }
                )
                
                # 플레이어 도시들의 식량과 생산력 정보 조회
                total_food = 0
                total_production = 0
                
                if player_civ:
                    player_cities = await prisma.city.find_many(
                        where={
                            "gameCivId": player_civ.id
                        }
                    )
                    
                    if player_cities:
                        for city in player_cities:
                            total_food += city.food
                            total_production += city.production
                
                # 플레이어 재화 정보 추가
                player_resources = {
                    "gold": player_civ.gold if player_civ else 0,
                    "science": player_civ.science if player_civ else 0,
                    "culture": player_civ.culture if player_civ else 0,
                    "food": total_food,
                    "production": total_production
                }
                
                # TurnSnapshot 업데이트 시도 - 에러 무시
                try:
                    await prisma.turnsnapshot.update(
                        where={"id": turn_snapshot.id},
                        data={
                            "playerResources": player_resources,
                            "stateData": state_data,
                            "observedMap": getattr(turn_snapshot, 'observedMap', {}),
                            "civId": getattr(turn_snapshot, 'civId', None),
                            "diplomacyState": getattr(turn_snapshot, 'diplomacyState', {}),
                            "productionState": getattr(turn_snapshot, 'productionState', {}),
                            "researchState": getattr(turn_snapshot, 'researchState', {})
                        }
                    )
                except Exception as update_error:
                    logger.error(f"TurnSnapshot 업데이트 중 오류: {str(update_error)}")
        
        return {
            "success": True,
            "status_code": 200,
            "message": f"턴 {query_turn}의 게임 상태를 조회했습니다.",
            "data": state_data,
            "player_resources": player_resources,
            "meta": {
                "game_id": game.id,
                "turn": query_turn,
                "current_turn": game.currentTurn,
                "created_at": datetime.now().isoformat()
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

# /turn/next 엔드포인트는 /turn/end로 병합됨. 모든 턴 진행 로직은 end_turn에서 처리합니다.
# (기존 next_turn 함수는 제거됨)
        next_year = request.next_year if request.next_year is not None else -4000 + 10 * next_turn_number
        
        # Medieval부터 시작, 시대별로 턴당 연도 증가 폭 다르게
        start_year = 1000 if request.next_year is None else request.next_year
        turn = next_turn_number if request.turn is not None else 1
        
        if turn < 11:
            era = "Medieval"
            year = start_year + (turn - 1) * 50
        elif turn < 21:
            era = "Industrial"
            year = start_year + 10 * 50 + (turn - 11) * 25
        else:
            era = "Modern"
            year = start_year + 10 * 50 + 10 * 25 + (turn - 21) * 10
        next_year = year
        # 시대와 연도는 위에서 계산한 값 사용
            
        # 현재 문명 정보 가져오기
        player_civ = await prisma.gameciv.find_first(
            where={
                "gameId": request.gameId,
                "isPlayer": True
            }
        )
        
        if not player_civ:
            raise HTTPException(status_code=404, detail="플레이어 문명을 찾을 수 없습니다")
        
        # 플레이어 도시 정보 가져오기 
        player_cities = await prisma.city.find_many(
            where={
                "gameCivId": player_civ.id
            },
            include={
                "buildings": True  # 도시의 건물 정보 포함
            }
        )
        
        # 연구된 기술 가져오기
        researched_techs = await prisma.gamecivtechnology.find_many(
            where={
                "gameCivId": player_civ.id,
                "status": "completed"
            },
            include={
                "technology": True  # 기술 정보 포함
            }
        )
            
        # 기본 자원 수입 계산
        base_gold_income = 5
        base_science_income = 2
        base_culture_income = 1
        base_food_income = 3
        base_production_income = 2
        
        # 건물 효과 계산
        buildings_gold_bonus = 0
        buildings_science_bonus = 0
        buildings_culture_bonus = 0
        buildings_food_bonus = 0
        buildings_production_bonus = 0
        
        # 도시별 건물 효과 계산
        for city in player_cities:
            # 도시당 기본 생산량 추가
            base_gold_income += 2
            base_science_income += 1
            base_food_income += 2
            base_production_income += 2
            
            # 도시 인구에 따른 추가 보너스
            base_food_income += city.population - 1  # 인구 1당 식량 +1 (초기 인구 제외)
            base_production_income += (city.population - 1) // 2  # 인구 2당 생산력 +1
            
            # 건물 효과 적용
            for building in city.buildings:
                # 건물 타입에 따른 추가 수입
                building_type = building.buildingType
                
                if "Market" in building_type or "Bank" in building_type or "Treasury" in building_type:
                    buildings_gold_bonus += 3
                elif "Library" in building_type or "University" in building_type or "Laboratory" in building_type:
                    buildings_science_bonus += 2
                elif "Temple" in building_type or "Monument" in building_type or "Theatre" in building_type:
                    buildings_culture_bonus += 2
                elif "Granary" in building_type or "Farm" in building_type or "Aqueduct" in building_type:
                    buildings_food_bonus += 2
                elif "Workshop" in building_type or "Factory" in building_type or "Mine" in building_type:
                    buildings_production_bonus += 2
                # 복합 효과 건물
                elif "Palace" in building_type:
                    buildings_gold_bonus += 2
                    buildings_culture_bonus += 1
                    buildings_science_bonus += 1
        
        # 기술 효과 계산
        tech_gold_bonus = 0
        tech_science_bonus = 0
        tech_culture_bonus = 0
        tech_food_bonus = 0
        tech_production_bonus = 0
        
        # 연구된 기술별 효과 계산
        for tech_entry in researched_techs:
            tech = tech_entry.technology
            tech_name = tech.name.lower()
            tech_era = tech.era
            
            # 기술 이름별 보너스 (예시)
            if "currency" in tech_name or "banking" in tech_name or "economics" in tech_name:
                tech_gold_bonus += 3
            elif "writing" in tech_name or "education" in tech_name or "science" in tech_name:
                tech_science_bonus += 2
            elif "drama" in tech_name or "literature" in tech_name or "philosophy" in tech_name:
                tech_culture_bonus += 2
            elif "agriculture" in tech_name or "irrigation" in tech_name or "botany" in tech_name:
                tech_food_bonus += 2
            elif "mining" in tech_name or "metallurgy" in tech_name or "engineering" in tech_name:
                tech_production_bonus += 2
            
            # 시대별 추가 보너스
            if tech_era == "Industrial" or tech_era == "Modern":
                tech_gold_bonus += 1
                tech_production_bonus += 1
            elif tech_era == "Atomic" or tech_era == "Information" or tech_era == "Future":
                tech_gold_bonus += 2
                tech_production_bonus += 2
                tech_science_bonus += 1
        
        # 전체 수입 계산
        total_gold_income = base_gold_income + buildings_gold_bonus + tech_gold_bonus
        total_science_income = base_science_income + buildings_science_bonus + tech_science_bonus
        total_culture_income = base_culture_income + buildings_culture_bonus + tech_culture_bonus
        total_food_income = base_food_income + buildings_food_bonus + tech_food_bonus
        total_production_income = base_production_income + buildings_production_bonus + tech_production_bonus
        
        # 다음 턴의 자원 상태 계산
        resources = {}
        if request.game_summary and hasattr(request.game_summary, 'resources') and request.game_summary.resources:
            resources = request.game_summary.resources
            
        next_resources = {
            "gold": resources.get("gold", 0) + total_gold_income,
            "science": resources.get("science", 0) + total_science_income,
            "culture": resources.get("culture", 0) + total_culture_income,
            "food": resources.get("food", 0) + total_food_income,
            "production": resources.get("production", 0) + total_production_income
        }
        
        # 자원 수입 내역 상세 정보
        resource_income_details = {
            "gold": {
                "base": base_gold_income,
                "buildings": buildings_gold_bonus,
                "tech": tech_gold_bonus,
                "total": total_gold_income
            },
            "science": {
                "base": base_science_income,
                "buildings": buildings_science_bonus,
                "tech": tech_science_bonus,
                "total": total_science_income
            },
            "culture": {
                "base": base_culture_income,
                "buildings": buildings_culture_bonus,
                "tech": tech_culture_bonus,
                "total": total_culture_income
            },
            "food": {
                "base": base_food_income,
                "buildings": buildings_food_bonus,
                "tech": tech_food_bonus,
                "total": total_food_income
            },
            "production": {
                "base": base_production_income,
                "buildings": buildings_production_bonus,
                "tech": tech_production_bonus,
                "total": total_production_income
            }
        }
        
        # 새로운 상태 데이터 생성
        new_state_data = {
            "turn": next_turn_number,
            "year": next_year,
            "era": era,
            "player_civ": {
                "id": player_civ.id,
                "name": player_civ.civType.name if player_civ and player_civ.civType else f"문명 {player_civ.id}",
                "leader": player_civ.civType.leaderName if player_civ and player_civ.civType else "알 수 없는 지도자"
            },
            "cities": [],  # 도시 목록 (업데이트 필요)
            "units": [],    # 유닛 목록 (업데이트 필요)
            "resourceIncome": resource_income_details  # 자원 수입 상세 정보 추가
        }
        # 새로운 턴 스냅샷 생성
        import json
        # 프론트에서 전달받은 맵/연구 상태 반영
        observed_map = getattr(game_summary, 'mapState', None) or {}
        research_state = getattr(game_summary, 'technologies', None) or {}

        new_snapshot = await prisma.turnsnapshot.create(
            data={
                "gameId": request.gameId,
                "turnNumber": next_turn_number,
                "year": next_year,  # year 필드 추가
                "civId": player_civ.id,
                "observedMap": json.dumps(observed_map),
                "researchState": json.dumps(research_state),
                "productionState": json.dumps({}),
                "diplomacyState": json.dumps({}),
                "resourceState": json.dumps(next_resources),
                "stateData": json.dumps(new_state_data),
                "playerResources": next_resources
            }
        )
        
        # 플레이어 문명 자원 업데이트
        await prisma.civilization.update(
            where={
                "id": player_civ.id
            },
            data={
                "gold": next_resources.get("gold"),
                "science": next_resources.get("science"),
                "culture": next_resources.get("culture")
            }
        )
        
        # 게임 업데이트 (현재 턴 정보)
        await prisma.game.update(
            where={
                "id": request.gameId
            },
            data={
                "currentTurn": next_turn_number,
                "currentYear": next_year,
                "updatedAt": datetime.now()
            }
        )
        
        # 게임 요약 생성
        game_summary = GameSummary(
            gameId=request.gameId,
            userId=game.userId,
            turn=next_turn_number,
            year=next_year,
            difficulty=game.difficulty,
            mapType=game.mapType,
            gameMode=game.gameMode,
            victoryType=None,  # 아직 승리 조건 미달성
            civilization={
                "id": player_civ.id,
                "name": player_civ.civType.name if player_civ and player_civ.civType else f"문명 {player_civ.id}",
                "leader": player_civ.civType.leaderName if player_civ and player_civ.civType else "알 수 없는 지도자",
                "color": player_civ.color
            },
            resources=next_resources,
            cities=[],
            units=[],
            technologies=[],  # 연구된 기술 목록 (구현 필요)
            diplomacy={},  # 외교 관계 (구현 필요)
            stats={
                "score": 0,  # 점수 (구현 필요)
                "militaryStrength": 0,  # 군사력 (구현 필요)
                "sciencePower": 0,  # 과학력 (구현 필요)
                "culturePower": 0  # 문화력 (구현 필요)
            },
            mapState={
                "fog": True,  # 안개 시스템 사용 여부
                "revealedTiles": 0,  # 발견한 타일 수 (구현 필요)
            },
            gameStatus="ACTIVE"
        )
        
        return {
            "success": True,
            "message": f"턴 {next_turn_number}로 진행되었습니다. 현재 연도: {next_year}",
            "turn": next_turn_number,
            "year": next_year,
            "era": era,
            "game_summary": game_summary,
            "resource_income": resource_income_details
        }
        
    except Exception as e:
        print(f"턴 진행 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"턴 진행 중 오류 발생: {str(e)}")

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
        queue_list = await prisma.researchqueue.find_many(
            where={"gameCivId": game_civ_id}
        )
        queue_list = sorted(queue_list, key=lambda x: x.queuePosition)
        queue_entry = queue_list[0] if queue_list else None
        
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
                        "decrement": 1
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
        queue_list = await prisma.buildqueue.find_many(
            where={"cityId": city_id}
        )
        queue_list = sorted(queue_list, key=lambda x: x.queueOrder)
        queue_entry = queue_list[0] if queue_list else None
        
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
        where={"id": civ_id},
        include={"civType": True}
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
        }
    )
    
    in_progress_tech = await prisma.gamecivtechnology.find_first(
        where={
            "gameCivId": civ_id,
            "status": "in_progress"
        }
    )
    
    research_queue = await prisma.researchqueue.find_many(
        where={"gameCivId": civ_id}
    )
    
    sorted_research_queue = sorted(research_queue, key=lambda x: x.queuePosition)
    
    # 최종 데이터 구성
    civ_data = {
        "id": civ.id,
        "name": civ.civType.name if hasattr(civ, 'civType') and civ.civType else f"문명 {civ.id}",
        "leader": civ.civType.leaderName if hasattr(civ, 'civType') and civ.civType else "알 수 없는 지도자",
        "cities": city_data,
        "research": {
            "completed": [],
            "in_progress": None,
            "queue": [{"id": r.techId} for r in sorted_research_queue]
        },
        "resources": {
            "gold": civ.gold,
            "science": civ.science,
            "culture": civ.culture
        }
    }
    # completed 기술 상세 정보 추가
    completed_techs_data = []
    for t in completed_techs:
        tech_obj = await prisma.technology.find_unique(where={"id": t.techId})
        completed_techs_data.append({
            "id": t.techId,
            "name": tech_obj.name if tech_obj else None,
            "required": tech_obj.researchCost if tech_obj else None
        })
    civ_data["research"]["completed"] = completed_techs_data
    # in_progress_tech가 있으면 기술 상세 정보 추가
    if in_progress_tech:
        tech = await prisma.technology.find_unique(where={"id": in_progress_tech.techId})
        civ_data["research"]["in_progress"] = {
            "id": in_progress_tech.techId,
            "name": tech.name if tech else None,
            "progress": in_progress_tech.progressPoints,
            "required": tech.researchCost if tech else None
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
                
                # 건설 큐에서 있는 건물 제외
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
    production_queue = await prisma.productionqueue.find_many(
        where={
            "cityId": city_id,
            "itemType": "unit"
        }
    )
    production_queue = sorted(production_queue, key=lambda x: x.queueOrder)
    current_production = production_queue[0] if production_queue else None
    
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
    """도시별 자원(식량, 생산력, 골드, 과학, 문화) 수집을 업데이트합니다."""
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
    culture_income = 4  # 기본 문화 수확량 추가
    
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
        elif building.building.category == "Culture":
            if building.building.name == "극장" or building.building.name == "박물관":
                culture_income += 5
    
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
            "science": {"increment": science_income},
            "culture": {"increment": culture_income}
        }
    )
    
    return {
        "food": food_income,
        "production": production_income,
        "gold": gold_income,
        "science": science_income,
        "culture": culture_income
    }

async def save_game_summary(game_summary: GameSummary):
    """게임 요약 정보를 저장하는 함수"""
    try:
        # 게임 요약 정보를 JSON으로 변환
        game_summary_json = game_summary.dict()
        
        # 게임 요약 정보를 데이터베이스에 저장
        await prisma.gamesummary.upsert(
            where={
                "gameId_turn": {
                    "gameId": game_summary.gameId,
                    "turn": game_summary.turn
                }
            },
            create={
                "gameId": game_summary.gameId,
                "turn": game_summary.turn,
                "data": game_summary_json
            },
            update={
                "data": game_summary_json,
                "updatedAt": datetime.now()
            }
        )
        
        logger.info(f"게임 요약 정보가 저장되었습니다. 게임 ID: {game_summary.gameId}, 턴: {game_summary.turn}")
        return True
    except Exception as e:
        logger.error(f"게임 요약 정보 저장 중 오류 발생: {str(e)}")
        return False

async def collect_and_save_game_summary(game_id: str, turn: int):
    """게임 상태를 분석하여 요약 정보를 수집하고 저장하는 함수"""
    try:
        # 게임 정보 조회
        game = await prisma.game.find_unique(
            where={"id": game_id}
        )
        
        if not game:
            logger.error(f"게임 요약 정보 수집 실패: 게임을 찾을 수 없습니다. 게임 ID: {game_id}")
            return False
        
        # 현재 턴의 게임 상태 조회 (TurnSnapshot 사용)
        game_states = await prisma.turnsnapshot.find_many(
            where={
                "gameId": game_id,
                "turnNumber": turn
            }
        )
        
        if not game_states or len(game_states) == 0:
            logger.error(f"게임 요약 정보 수집 실패: 게임 상태를 찾을 수 없습니다. 게임 ID: {game_id}, 턴: {turn}")
            return False
        
        current_state = game_states[0]
        state_data = current_state.stateData
        
        # 플레이어 문명 정보 조회
        player_civ = await prisma.gameciv.find_first(
            where={
                "gameId": game_id,
                "id": game.playerCivId
            }
        )
        
        # 플레이어 도시들의 평균 식량과 생산력 계산
        player_cities = await prisma.city.find_many(
            where={
                "gameCivId": game.playerCivId
            }
        )
        
        avg_food = 0
        avg_production = 0
        
        if player_cities and len(player_cities) > 0:
            total_food = sum(city.food for city in player_cities)
            total_production = sum(city.production for city in player_cities)
            avg_food = total_food // len(player_cities)
            avg_production = total_production // len(player_cities)
        
        # 게임 상태로부터 요약 정보 생성
        game_summary = GameSummary(
            gameId=game_id,
            userId=game.userName,
            turn=turn,
            year=state_data.get("year"),
            difficulty=game.difficulty,
            mapType=game.mapType,
            gameMode=game.gameMode,
            startTime=game.createdAt,
            civilizationId=game.playerCivId,
            civilizationName=state_data.get("player_civ", {}).get("name"),
            leaderName=state_data.get("player_civ", {}).get("leader"),
            gold=player_civ.gold if player_civ else 0,
            science=player_civ.science if player_civ else 0,
            culture=player_civ.culture if player_civ else 0,
            food=avg_food,
            production=avg_production,
            resources=state_data.get("resources", {}),
            totalCities=len(state_data.get("cities", [])),
            totalUnits=len(state_data.get("units", [])),
        )
        
        # 게임 요약 정보 저장
        return await save_game_summary(game_summary)
    except Exception as e:
        logger.error(f"게임 요약 정보 수집 및 저장 중 오류 발생: {str(e)}")
        return False

async def update_research_queue(game_civ_id):
    """연구 큐의 위치 업데이트"""
    # 현재 연구 큐 가져오기
    research_queue = await prisma.researchqueue.find_many(
        where={"gameCivId": game_civ_id}
    )
    research_queue = sorted(research_queue, key=lambda x: x.queuePosition)
    # 큐 위치 업데이트
    for i, queue_item in enumerate(research_queue):
        if i > 0:  # 첫 번째 항목은 현재 연구 중인 기술이므로 제외
            await prisma.researchqueue.update(
                where={"id": queue_item.id},
                data={"queuePosition": i}
            )
    
    return True
