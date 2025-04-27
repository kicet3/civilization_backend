from fastapi import APIRouter, HTTPException, Query, Body, Path
from typing import List, Optional, Dict, Any
from enum import Enum
from db.client import prisma
from pydantic import BaseModel

router = APIRouter()

class BuildingCategory(str, Enum):
    Housing = "Housing"
    Production = "Production"
    Science = "Science"
    Defense = "Defense"
    Trade = "Trade"

class ResourceCost(BaseModel):
    Food: int = 0
    Production: int = 0
    Gold: int = 0
    Science: int = 0

class MaintenanceCost(BaseModel):
    Gold: int = 0

class BuildStatus(str, Enum):
    queued = "queued"
    in_progress = "in_progress"
    completed = "completed"

@router.get("/", summary="건물 목록 조회", response_description="건물 목록 반환")
async def get_buildings(
    category: Optional[BuildingCategory] = None,
    prereqTech: Optional[int] = None
):
    """건물 목록을 조회합니다."""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 조건 구성
        where_condition = {}
        
        if category:
            where_condition["category"] = category.value
        
        if prereqTech is not None:
            where_condition["prerequisiteTechId"] = prereqTech
        
        # 건물 목록 조회
        buildings = await prisma.building.find_many(
            where=where_condition
        )
        
        # 결과 변환
        result = []
        for building in buildings:
            # 실제로는 리소스 비용이 JSON 형태로 저장되어 있거나, 별도 테이블에 있을 수 있음
            # 여기서는 임의로 생성
            resource_cost = {
                "Food": 0,
                "Production": building.resourceCost,
                "Gold": 0,
                "Science": 0
            }
            
            maintenance_cost = {
                "Gold": building.maintenanceCost
            }
            
            result.append({
                "id": building.id,
                "name": building.name,
                "category": building.category,
                "description": building.description,
                "buildTime": building.buildTime,
                "resourceCost": resource_cost,
                "maintenanceCost": maintenance_cost,
                "prerequisiteTechId": building.prerequisiteTechId
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

@router.get("/{building_id}", summary="건물 상세 조회", response_description="건물 상세 정보 반환")
async def get_building_detail(building_id: int = Path(..., description="조회할 건물 ID")):
    """특정 건물의 상세 정보를 조회합니다."""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 건물 조회
        building = await prisma.building.find_unique(
            where={"id": building_id}
        )
        
        if not building:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "NotFoundError",
                    "detail": f"ID가 {building_id}인 건물을 찾을 수 없습니다."
                }
            }
        
        # 리소스 비용 및 유지 비용 (임의 생성)
        resource_cost = {
            "Food": 0,
            "Production": building.resourceCost,
            "Gold": 0,
            "Science": 0
        }
        
        maintenance_cost = {
            "Gold": building.maintenanceCost
        }
        
        # 결과 변환
        result = {
            "id": building.id,
            "name": building.name,
            "category": building.category,
            "description": building.description,
            "buildTime": building.buildTime,
            "resourceCost": resource_cost,
            "maintenanceCost": maintenance_cost,
            "prerequisiteTechId": building.prerequisiteTechId
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

@router.get("/cities/{city_id}/buildings", summary="도시 건물 조회", response_description="도시의 건물 목록 반환")
async def get_city_buildings(city_id: int = Path(..., description="조회할 도시 ID")):
    """특정 도시에 건설된 건물 목록을 조회합니다."""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 도시의 건물 조회
        player_buildings = await prisma.playerbuilding.find_many(
            where={
                "cityId": city_id
            },
            include={
                "building": True
            }
        )
        
        # 결과 변환
        result = []
        for player_building in player_buildings:
            result.append({
                "playerBuildingId": player_building.id,
                "buildingId": player_building.buildingId,
                "name": player_building.building.name,
                "status": player_building.status,
                "startedAt": player_building.startedAt,
                "completedAt": player_building.completedAt
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

@router.get("/cities/{city_id}/build-queue", summary="건설 큐 조회", response_description="도시의 건설 큐 반환")
async def get_build_queue(city_id: int = Path(..., description="조회할 도시 ID")):
    """특정 도시의 건설 큐를 조회합니다."""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 건설 큐 조회
        queue_entries = await prisma.buildqueue.find_many(
            where={
                "cityId": city_id
            },
            include={
                "building": True
            }
        )
        
        # 결과 변환 및 수동 정렬
        result = sorted([
            {
                "queueId": entry.id,
                "buildingId": entry.buildingId,
                "name": entry.building.name,
                "queuePosition": entry.queueOrder
            }
            for entry in queue_entries
        ], key=lambda x: x["queuePosition"])
        
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

@router.post("/cities/{city_id}/build-queue", summary="건설 큐에 추가", response_description="건설 큐 추가 결과")
async def add_to_build_queue(
    building_request: Dict[str, int] = Body(..., example={"buildingId": 5}),
    city_id: int = Path(..., description="도시 ID")
):
    """건설 큐에 새 건물을 추가합니다."""
    try:
        building_id = building_request.get("buildingId")
        if not building_id:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "ValidationError",
                    "detail": "유효한 buildingId를 제공해야 합니다."
                }
            }
        
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 건물 존재 확인
        building = await prisma.building.find_unique(
            where={"id": building_id}
        )
        
        if not building:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "NotFoundError",
                    "detail": f"ID가 {building_id}인 건물을 찾을 수 없습니다."
                }
            }
        
        # 도시 존재 확인
        city = await prisma.city.find_unique(
            where={"id": city_id}
        )
        
        if not city:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "NotFoundError",
                    "detail": f"ID가 {city_id}인 도시를 찾을 수 없습니다."
                }
            }
        
        # 현재 큐 크기 확인
        current_queue = await prisma.buildqueue.find_many(
            where={
                "cityId": city_id
            }
        )
        
        # 새 큐 위치 계산
        next_position = 1
        if current_queue:
            next_position = max(entry.queueOrder for entry in current_queue) + 1
        
        # 건설 큐에 추가
        new_queue_entry = await prisma.buildqueue.create(
            data={
                "cityId": city_id,
                "buildingId": building_id,
                "queueOrder": next_position,
                "addedAt": prisma.datetime.now()
            }
        )
        
        result = {
            "queueId": new_queue_entry.id,
            "buildingId": new_queue_entry.buildingId,
            "queuePosition": new_queue_entry.queueOrder
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

@router.delete("/cities/{city_id}/build-queue/{queue_id}", summary="건설 큐에서 제거", response_description="건설 큐 제거 결과")
async def remove_from_build_queue(
    city_id: int = Path(..., description="도시 ID"),
    queue_id: int = Path(..., description="큐 ID")
):
    """건설 큐에서 건물을 제거합니다."""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 큐 엔트리 확인
        queue_entry = await prisma.buildqueue.find_unique(
            where={
                "id": queue_id
            }
        )
        
        if not queue_entry or queue_entry.cityId != city_id:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "NotFoundError",
                    "detail": f"ID가 {queue_id}인 큐 엔트리를 찾을 수 없거나 접근 권한이 없습니다."
                }
            }
        
        # 제거할 큐 엔트리의 위치 저장
        removed_position = queue_entry.queueOrder
        
        # 큐 엔트리 제거
        await prisma.buildqueue.delete(
            where={
                "id": queue_id
            }
        )
        
        # 다른 큐 엔트리의 위치 재조정
        await prisma.buildqueue.update_many(
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
        
        return {
            "success": True,
            "data": None,
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

@router.post("/cities/{city_id}/build/start", summary="건설 즉시 시작", response_description="건설 시작 결과")
async def start_building(
    building_request: Dict[str, int] = Body(..., example={"buildingId": 4}),
    city_id: int = Path(..., description="도시 ID")
):
    """특정 건물의 건설을 즉시 시작합니다."""
    try:
        building_id = building_request.get("buildingId")
        if not building_id:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "ValidationError",
                    "detail": "유효한 buildingId를 제공해야 합니다."
                }
            }
        
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 도시 존재 확인
        city = await prisma.city.find_unique(
            where={"id": city_id}
        )
        
        if not city:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "NotFoundError",
                    "detail": f"ID가 {city_id}인 도시를 찾을 수 없습니다."
                }
            }
        
        # 건물 존재 확인
        building = await prisma.building.find_unique(
            where={"id": building_id}
        )
        
        if not building:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "NotFoundError",
                    "detail": f"ID가 {building_id}인 건물을 찾을 수 없습니다."
                }
            }
        
        # 이미 건설 중인 건물이 있는지 확인
        in_progress = await prisma.playerbuilding.find_first(
            where={
                "cityId": city_id,
                "status": "in_progress"
            }
        )
        
        if in_progress:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "ConflictError",
                    "detail": f"이미 건설 중인 건물이 있습니다 (ID: {in_progress.buildingId})."
                }
            }
        
        # 이미 도시에 같은 건물이 있는지 확인
        existing_building = await prisma.playerbuilding.find_first(
            where={
                "cityId": city_id,
                "buildingId": building_id,
                "status": "completed"
            }
        )
        
        if existing_building:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "ConflictError",
                    "detail": f"이 도시에는 이미 이 건물이 건설되어 있습니다 (ID: {building_id})."
                }
            }
        
        # 건설 시작
        player_building = await prisma.playerbuilding.create(
            data={
                "cityId": city_id,
                "buildingId": building_id,
                "gameCivId": city.gameCivId,
                "status": "in_progress",
                "startedAt": prisma.datetime.now()
            }
        )
        
        result = {
            "playerBuildingId": player_building.id,
            "buildingId": player_building.buildingId,
            "status": player_building.status,
            "startedAt": player_building.startedAt
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

@router.post("/cities/{city_id}/build/cancel", summary="건설 취소", response_description="건설 취소 결과")
async def cancel_building(
    building_request: Dict[str, int] = Body(..., example={"playerBuildingId": 104}),
    city_id: int = Path(..., description="도시 ID")
):
    """진행 중인 건물 건설을 취소합니다."""
    try:
        player_building_id = building_request.get("playerBuildingId")
        if not player_building_id:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "ValidationError",
                    "detail": "유효한 playerBuildingId를 제공해야 합니다."
                }
            }
        
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 건설 중인 건물 확인
        player_building = await prisma.playerbuilding.find_unique(
            where={"id": player_building_id}
        )
        
        if not player_building or player_building.cityId != city_id:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "NotFoundError",
                    "detail": f"ID가 {player_building_id}인 건물을 찾을 수 없거나 접근 권한이 없습니다."
                }
            }
        
        if player_building.status != "in_progress":
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "ConflictError",
                    "detail": f"이 건물은 현재 건설 중이 아닙니다 (상태: {player_building.status})."
                }
            }
        
        # 건설 중인 건물 제거
        await prisma.playerbuilding.delete(
            where={"id": player_building_id}
        )
        
        return {
            "success": True,
            "data": None,
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