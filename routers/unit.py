from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional, Dict, Any
from db.client import prisma
from enum import Enum
from fastapi.responses import JSONResponse
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

class UnitCategory(str, Enum):
    Melee = "Melee"
    Ranged = "Ranged"
    Cavalry = "Cavalry"
    Siege = "Siege"
    Modern = "Modern"
    Civilian = "Civilian"

class EraType(str, Enum):
    Medieval = "Medieval"
    Industrial = "Industrial"
    Modern = "Modern"

class ItemType(str, Enum):
    unit = "unit"
    building = "building"

class UnitProductionRequest(BaseModel):
    unit_type_id: int

class UnitQueueResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.get("/", summary="유닛 목록 조회", response_description="유닛 목록 반환")
async def get_units(
    era: Optional[EraType] = None,
    category: Optional[UnitCategory] = None,
    prereqTech: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """유닛 목록을 조회합니다."""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 조건 구성
        where_condition = {}
        
        if era:
            where_condition["era"] = era.value
        
        if category:
            where_condition["category"] = category.value
        
        if prereqTech is not None:
            where_condition["prereqTechId"] = prereqTech
        
        # 유닛 목록 조회
        units = await prisma.unittype.find_many(
            where=where_condition,
            skip=offset,
            take=limit
        )
        
        # 결과 변환
        result = []
        for unit in units:
            result.append({
                "id": unit.id,
                "name": unit.name,
                "category": unit.category,
                "era": unit.era,
                "maintenance": unit.maintenance,
                "movement": unit.movement,
                "sight": unit.sight,
                "buildTime": unit.buildTime,
                "prereqTechId": unit.prereqTechId
            })
        
        return {
            "success": True,
            "data": result,
            "error": None
        }
    
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": {
                "type": type(e).__name__,
                "detail": str(e)
            }
        }

@router.get("/{unit_id}", summary="유닛 상세 조회", response_description="유닛 상세 정보 반환")
async def get_unit_detail(unit_id: int):
    """특정 유닛의 상세 정보를 조회합니다."""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 유닛 조회
        unit = await prisma.unittype.find_unique(
            where={"id": unit_id}
        )
        
        if not unit:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "NotFoundError",
                    "detail": f"ID가 {unit_id}인 유닛을 찾을 수 없습니다."
                }
            }
        
        # 결과 변환
        result = {
            "id": unit.id,
            "name": unit.name,
            "category": unit.category,
            "era": unit.era,
            "maintenance": unit.maintenance,
            "movement": unit.movement,
            "sight": unit.sight,
            "buildTime": unit.buildTime,
            "prereqTechId": unit.prereqTechId
        }
        
        return {
            "success": True,
            "data": result,
            "error": None
        }
    
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": {
                "type": type(e).__name__,
                "detail": str(e)
            }
        }

@router.post("/cities/{city_id}/produce-unit", summary="유닛 생산 시작", response_description="유닛 생산 시작 결과")
async def produce_unit(
    city_id: int = Path(..., description="도시 ID"),
    request: UnitProductionRequest = None
):
    """특정 도시에서 유닛 생산을 시작하거나 생산 큐에 추가합니다."""
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
        
        # 도시 존재 확인
        city = await prisma.city.find_unique(
            where={"id": city_id}
        )
        
        if not city:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "data": None,
                    "error": f"도시 ID {city_id}에 해당하는 도시를 찾을 수 없습니다."
                }
            )
        
        # 유닛 타입 확인
        unit_type = await prisma.unittype.find_unique(
            where={"id": request.unit_type_id}
        )
        
        if not unit_type:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "data": None,
                    "error": f"유닛 타입 ID {request.unit_type_id}에 해당하는 유닛을 찾을 수 없습니다."
                }
            )
        
        # 선행 기술 확인
        if unit_type.prereqTechId:
            completed_techs = await prisma.gamecivtechnology.find_many(
                where={
                    "gameCivId": city.gameCivId,
                    "status": "completed"
                }
            )
            
            completed_tech_ids = [tech.techId for tech in completed_techs]
            
            if unit_type.prereqTechId not in completed_tech_ids:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "data": None,
                        "error": f"선행 기술(ID: {unit_type.prereqTechId})이 연구되지 않았습니다."
                    }
                )
        
        # 현재 건설/생산 중인 항목 확인
        # 1. 건물 건설 확인
        in_progress_building = await prisma.playerbuilding.find_first(
            where={
                "cityId": city_id,
                "status": "in_progress"
            }
        )
        
        # 2. 현재 유닛 생산 확인
        in_progress_production = await prisma.productionqueue.find_first(
            where={
                "cityId": city_id,
                "queueOrder": 1
            }
        )
        
        # 도시가 이미 다른 작업 중인지 확인
        if in_progress_building or in_progress_production:
            # 생산 큐에 추가
            current_queue = await prisma.productionqueue.find_many(
                where={"cityId": city_id}
            )
            
            next_position = 1
            if current_queue:
                next_position = max(entry.queueOrder for entry in current_queue) + 1
            
            # 유닛의 생산 시간 계산 (턴 단위)
            turns_left = unit_type.buildTime
            
            # 생산 큐에 추가
            queue_entry = await prisma.productionqueue.create(
                data={
                    "cityId": city_id,
                    "itemId": request.unit_type_id,
                    "itemType": "unit",
                    "queueOrder": next_position,
                    "turnsLeft": turns_left,
                    "addedAt": datetime.now()
                }
            )
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": {
                        "message": "유닛 생산이 생산 큐에 추가되었습니다.",
                        "queue_position": next_position,
                        "unit_type": {
                            "id": unit_type.id,
                            "name": unit_type.name,
                            "category": unit_type.category
                        },
                        "turns_left": turns_left
                    },
                    "error": None
                }
            )
        else:
            # 바로 생산 시작
            # 유닛의 생산 시간 계산 (턴 단위)
            turns_left = unit_type.buildTime
            
            # 생산 큐에 추가 (첫 번째 위치)
            queue_entry = await prisma.productionqueue.create(
                data={
                    "cityId": city_id,
                    "itemId": request.unit_type_id,
                    "itemType": "unit",
                    "queueOrder": 1,
                    "turnsLeft": turns_left,
                    "addedAt": datetime.now()
                }
            )
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": {
                        "message": "유닛 생산이 시작되었습니다.",
                        "unit_type": {
                            "id": unit_type.id,
                            "name": unit_type.name,
                            "category": unit_type.category
                        },
                        "turns_left": turns_left
                    },
                    "error": None
                }
            )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": f"서버 오류: {str(e)}"
            }
        )

@router.get("/cities/{city_id}/production-queue", summary="유닛 생산 큐 조회", response_description="유닛 생산 큐 정보")
async def get_production_queue(city_id: int = Path(..., description="도시 ID")):
    """특정 도시의 유닛 생산 큐를 조회합니다."""
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
        
        # 도시 존재 확인
        city = await prisma.city.find_unique(
            where={"id": city_id}
        )
        
        if not city:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "data": None,
                    "error": f"도시 ID {city_id}에 해당하는 도시를 찾을 수 없습니다."
                }
            )
        
        # 생산 큐 조회
        production_queue = await prisma.productionqueue.find_many(
            where={
                "cityId": city_id,
                "itemType": "unit"
            },
            order_by={
                "queueOrder": "asc"
            }
        )
        
        # 결과 변환
        queue_items = []
        for item in production_queue:
            # 유닛 타입 정보 가져오기
            unit_type = await prisma.unittype.find_unique(
                where={"id": item.itemId}
            )
            
            if unit_type:
                queue_items.append({
                    "queue_id": item.id,
                    "position": item.queueOrder,
                    "turns_left": item.turnsLeft,
                    "unit_type": {
                        "id": unit_type.id,
                        "name": unit_type.name,
                        "category": unit_type.category,
                        "era": unit_type.era
                    },
                    "added_at": item.addedAt.isoformat()
                })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "city_id": city_id,
                    "city_name": city.name,
                    "queue_items": queue_items
                },
                "error": None
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": f"서버 오류: {str(e)}"
            }
        )

@router.delete("/cities/{city_id}/production-queue/{queue_id}", summary="유닛 생산 큐에서 제거", response_description="유닛 생산 큐 제거 결과")
async def cancel_unit_production(
    city_id: int = Path(..., description="도시 ID"),
    queue_id: int = Path(..., description="큐 항목 ID")
):
    """유닛 생산 큐에서 특정 항목을 제거합니다."""
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
        
        # 큐 항목 확인
        queue_item = await prisma.productionqueue.find_unique(
            where={"id": queue_id}
        )
        
        if not queue_item:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "data": None,
                    "error": f"큐 항목 ID {queue_id}에 해당하는 항목을 찾을 수 없습니다."
                }
            )
        
        # 도시 확인
        if queue_item.cityId != city_id:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "data": None,
                    "error": f"큐 항목이 도시 ID {city_id}에 속하지 않습니다."
                }
            )
        
        # 제거할 항목의 위치 저장
        removed_position = queue_item.queueOrder
        
        # 큐에서 제거
        await prisma.productionqueue.delete(
            where={"id": queue_id}
        )
        
        # 나머지 큐 재정렬
        await prisma.productionqueue.update_many(
            where={
                "cityId": city_id,
                "queueOrder": {
                    "gt": removed_position
                }
            },
            data={
                "queueOrder": {
                    "decrement": 1
                }
            }
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "message": "유닛 생산이 취소되었습니다."
                },
                "error": None
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": f"서버 오류: {str(e)}"
            }
        )

@router.get("/cities/{city_id}/units", summary="도시 생산 유닛 목록 조회", response_description="도시가 생산한 유닛 목록")
async def get_city_units(city_id: int = Path(..., description="도시 ID")):
    """특정 도시에서 생산된 유닛 목록을 조회합니다."""
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
        
        # 도시 존재 확인
        city = await prisma.city.find_unique(
            where={"id": city_id}
        )
        
        if not city:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "data": None,
                    "error": f"도시 ID {city_id}에 해당하는 도시를 찾을 수 없습니다."
                }
            )
        
        # 이 도시 주변의 유닛 조회 (q, r 좌표가 도시의 좌표와 일치하거나 인접한 경우)
        # 간단한 구현을 위해 도시의 gameCivId를 활용
        units = await prisma.gameunit.find_many(
            where={
                "gameCivId": city.gameCivId,
                "OR": [
                    # 도시 좌표와 일치
                    {
                        "q": city.q,
                        "r": city.r
                    },
                    # 인접한 6개 hexagon 좌표
                    # 상단 (+0, -1)
                    {
                        "q": city.q,
                        "r": city.r - 1
                    },
                    # 우상단 (+1, -1)
                    {
                        "q": city.q + 1,
                        "r": city.r - 1
                    },
                    # 우하단 (+1, +0)
                    {
                        "q": city.q + 1,
                        "r": city.r
                    },
                    # 하단 (+0, +1)
                    {
                        "q": city.q,
                        "r": city.r + 1
                    },
                    # 좌하단 (-1, +1)
                    {
                        "q": city.q - 1,
                        "r": city.r + 1
                    },
                    # 좌상단 (-1, +0)
                    {
                        "q": city.q - 1,
                        "r": city.r
                    }
                ]
            },
            include={
                "unitType": True
            }
        )
        
        # 결과 변환
        result = []
        for unit in units:
            result.append({
                "id": unit.id,
                "type": {
                    "id": unit.unitType.id,
                    "name": unit.unitType.name,
                    "category": unit.unitType.category
                },
                "location": {
                    "q": unit.q,
                    "r": unit.r
                },
                "hp": unit.hp,
                "created_turn": unit.createdTurn,
                "promotion_level": unit.promotionLevel
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "city_id": city_id,
                    "city_name": city.name,
                    "units": result
                },
                "error": None
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": f"서버 오류: {str(e)}"
            }
        ) 