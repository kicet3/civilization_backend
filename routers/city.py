from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Dict, Any, Optional
from models.city import CityResponse, CityProduceRequest, CitySpecializeRequest
from core.config import prisma_client
from utils.production_utils import add_to_production_queue, update_queue_order
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/{game_id}/cities", response_model=List[CityResponse])
async def get_cities(game_id: str, player_id: Optional[int] = None):
    """게임의 도시 목록 조회 API
    
    player_id가 제공되면 해당 플레이어의 도시만 반환, 아니면 모든 도시 반환
    """
    try:
        # 도시 조회 조건 설정
        where = {"session_id": game_id}
        if player_id is not None:
            where["owner_player_id"] = player_id
            
        # 도시 목록 조회 (건물, 생산 큐 포함)
        cities = await prisma_client.city.find_many(
            where=where,
            include={
                "buildings": True,
                "production_queue": {
                    "orderBy": {
                        "queue_order": "asc"
                    }
                }
            }
        )
        
        # 응답 모델로 변환
        city_responses = []
        for city in cities:
            # 생산 큐 아이템 변환
            production_queue = []
            for item in city.production_queue:
                # 아이템 이름 조회 (유닛 또는 건물)
                item_name = ""
                if item.itemType == "unit":
                    unit_type = await prisma_client.unitType.find_unique(
                        where={"id": item.itemId}
                    )
                    item_name = unit_type.name if unit_type else item.itemId
                elif item.itemType == "building":
                    building_type = await prisma_client.buildingType.find_unique(
                        where={"id": item.itemId}
                    )
                    item_name = building_type.name if building_type else item.itemId
                
                production_queue.append({
                    "id": item.id,
                    "itemType": item.itemType,
                    "itemId": item.itemId,
                    "name": item_name,
                    "turnsLeft": item.turns_left,
                    "queueOrder": item.queue_order
                })
            
            # 건물 목록 변환
            buildings = [
                {
                    "id": building.id,
                    "name": building.name,
                    "effects": building.effectJson
                }
                for building in city.buildings
            ]
            
            # 현재 생산 항목 정보
            current_production = None
            turns_left = None
            if production_queue:
                current_production = production_queue[0]["name"]
                turns_left = production_queue[0]["turnsLeft"]
            
            # 도시 응답 모델 생성
            city_response = CityResponse(
                id=str(city.id),
                name=city.name,
                population=city.population,
                hp=city.hp or 100,
                defense=city.defense or 10,
                food=city.food or 0,
                production=city.production or 0,
                gold=city.gold or 0,
                science=city.science or 0,
                culture=city.culture or 0,
                faith=city.faith or 0,
                happiness=city.happiness or 0,
                currentProduction=current_production,
                turnsLeft=turns_left,
                productionQueue=production_queue,
                foodToNextPop=city.food_to_next_pop or 10,
                cultureToNextBorder=city.culture_to_next_border or 20,
                location={
                    "q": city.loc_q or 0,
                    "r": city.loc_r or 0,
                    "s": city.loc_s or 0
                },
                buildings=buildings
            )
            
            city_responses.append(city_response)
        
        return city_responses
    
    except Exception as e:
        logger.error(f"도시 목록 조회 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"도시 목록 조회 중 오류 발생: {str(e)}"
        )

@router.get("/{game_id}/city/{city_id}", response_model=CityResponse)
async def get_city(game_id: str, city_id: int):
    """도시 상세 정보 조회 API"""
    try:
        # 도시 정보 조회 (건물, 생산 큐 포함)
        city = await prisma_client.city.find_first(
            where={
                "session_id": game_id,
                "id": city_id
            },
            include={
                "buildings": True,
                "production_queue": {
                    "orderBy": {
                        "queue_order": "asc"
                    }
                }
            }
        )
        
        if not city:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="도시를 찾을 수 없습니다"
            )
        
        # 생산 큐 아이템 변환
        production_queue = []
        for item in city.production_queue:
            # 아이템 이름 조회 (유닛 또는 건물)
            item_name = ""
            if item.itemType == "unit":
                unit_type = await prisma_client.unitType.find_unique(
                    where={"id": item.itemId}
                )
                item_name = unit_type.name if unit_type else item.itemId
            elif item.itemType == "building":
                building_type = await prisma_client.buildingType.find_unique(
                    where={"id": item.itemId}
                )
                item_name = building_type.name if building_type else item.itemId
            
            production_queue.append({
                "id": item.id,
                "itemType": item.itemType,
                "itemId": item.itemId,
                "name": item_name,
                "turnsLeft": item.turns_left,
                "queueOrder": item.queue_order
            })
        
        # 건물 목록 변환
        buildings = [
            {
                "id": building.id,
                "name": building.name,
                "effects": building.effectJson
            }
            for building in city.buildings
        ]
        
        # 현재 생산 항목 정보
        current_production = None
        turns_left = None
        if production_queue:
            current_production = production_queue[0]["name"]
            turns_left = production_queue[0]["turnsLeft"]
        
        # 도시 응답 모델 생성
        city_response = CityResponse(
            id=str(city.id),
            name=city.name,
            population=city.population,
            hp=city.hp or 100,
            defense=city.defense or 10,
            food=city.food or 0,
            production=city.production or 0,
            gold=city.gold or 0,
            science=city.science or 0,
            culture=city.culture or 0,
            faith=city.faith or 0,
            happiness=city.happiness or 0,
            currentProduction=current_production,
            turnsLeft=turns_left,
            productionQueue=production_queue,
            foodToNextPop=city.food_to_next_pop or 10,
            cultureToNextBorder=city.culture_to_next_border or 20,
            location={
                "q": city.loc_q or 0,
                "r": city.loc_r or 0,
                "s": city.loc_s or 0
            },
            buildings=buildings
        )
        
        return city_response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"도시 정보 조회 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"도시 정보 조회 중 오류 발생: {str(e)}"
        )

@router.get("/{game_id}/city/{city_id}/production")
async def get_production_queue(game_id: str, city_id: int):
    """도시 생산 큐 조회 API"""
    try:
        # 도시 존재 확인
        city = await prisma_client.city.find_first(
            where={
                "session_id": game_id,
                "id": city_id
            }
        )
        
        if not city:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="도시를 찾을 수 없습니다"
            )
        
        # 생산 큐 조회
        queue_items = await prisma_client.productionQueue.find_many(
            where={"city_id": city_id},
            orderBy={"queue_order": "asc"}
        )
        
        # 응답 데이터 변환
        result = []
        for item in queue_items:
            # 아이템 이름 조회 (유닛 또는 건물)
            item_name = ""
            if item.itemType == "unit":
                unit_type = await prisma_client.unitType.find_unique(
                    where={"id": item.itemId}
                )
                item_name = unit_type.name if unit_type else item.itemId
            elif item.itemType == "building":
                building_type = await prisma_client.buildingType.find_unique(
                    where={"id": item.itemId}
                )
                item_name = building_type.name if building_type else item.itemId
            
            result.append({
                "id": item.id,
                "itemType": item.itemType,
                "itemId": item.itemId,
                "name": item_name,
                "turnsLeft": item.turns_left,
                "queueOrder": item.queue_order
            })
        
        return {
            "queue": result,
            "cityProduction": city.production
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"생산 큐 조회 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"생산 큐 조회 중 오류 발생: {str(e)}"
        )

@router.post("/{game_id}/city/{city_id}/production", status_code=status.HTTP_201_CREATED)
async def add_production_item(game_id: str, city_id: int, request: CityProduceRequest):
    """생산 큐에 아이템 추가 API"""
    try:
        # 도시 존재 확인
        city = await prisma_client.city.find_first(
            where={
                "session_id": game_id,
                "id": city_id
            }
        )
        
        if not city:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="도시를 찾을 수 없습니다"
            )
        
        # 생산 큐에 아이템 추가
        item_type = request.itemType.value  # enum 값 추출
        queue_item = await add_to_production_queue(
            city_id=city_id,
            item_type=item_type,
            item_id=request.itemId
        )
        
        if not queue_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="생산 아이템 추가 실패"
            )
        
        # 생산 큐 다시 조회
        updated_queue = await prisma_client.productionQueue.find_many(
            where={"city_id": city_id},
            orderBy={"queue_order": "asc"}
        )
        
        # 응답 데이터 변환
        result = []
        for item in updated_queue:
            # 아이템 이름 조회 (유닛 또는 건물)
            item_name = ""
            if item.itemType == "unit":
                unit_type = await prisma_client.unitType.find_unique(
                    where={"id": item.itemId}
                )
                item_name = unit_type.name if unit_type else item.itemId
            elif item.itemType == "building":
                building_type = await prisma_client.buildingType.find_unique(
                    where={"id": item.itemId}
                )
                item_name = building_type.name if building_type else item.itemId
            
            result.append({
                "id": item.id,
                "itemType": item.itemType,
                "itemId": item.itemId,
                "name": item_name,
                "turnsLeft": item.turns_left,
                "queueOrder": item.queue_order
            })
        
        return {
            "success": True,
            "message": "생산 아이템이 추가되었습니다",
            "queue": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"생산 아이템 추가 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"생산 아이템 추가 중 오류 발생: {str(e)}"
        )

@router.patch("/{game_id}/city/{city_id}/production/{queue_id}")
async def update_production_item(game_id: str, city_id: int, queue_id: int, new_order: int = Query(...)):
    """생산 큐 아이템 순서 변경 API"""
    try:
        # 도시 존재 확인
        city = await prisma_client.city.find_first(
            where={
                "session_id": game_id,
                "id": city_id
            }
        )
        
        if not city:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="도시를 찾을 수 없습니다"
            )
        
        # 큐 아이템 존재 확인
        queue_item = await prisma_client.productionQueue.find_unique(
            where={"id": queue_id}
        )
        
        if not queue_item or queue_item.city_id != city_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="생산 큐 아이템을 찾을 수 없습니다"
            )
        
        # 생산 큐 목록 조회
        queue_items = await prisma_client.productionQueue.find_many(
            where={"city_id": city_id},
            orderBy={"queue_order": "asc"}
        )
        
        if new_order < 0 or new_order >= len(queue_items):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 순서입니다"
            )
        
        # 현재 순서
        current_order = queue_item.queue_order
        
        # 순서 변경
        if current_order < new_order:
            # 순서를 뒤로 이동 (현재 위치와 새 위치 사이의 아이템들은 앞으로 당김)
            await prisma_client.productionQueue.update_many(
                where={
                    "city_id": city_id,
                    "queue_order": {
                        "gt": current_order,
                        "lte": new_order
                    }
                },
                data={
                    "queue_order": {"decrement": 1}
                }
            )
        elif current_order > new_order:
            # 순서를 앞으로 이동 (현재 위치와 새 위치 사이의 아이템들은 뒤로 밀림)
            await prisma_client.productionQueue.update_many(
                where={
                    "city_id": city_id,
                    "queue_order": {
                        "gte": new_order,
                        "lt": current_order
                    }
                },
                data={
                    "queue_order": {"increment": 1}
                }
            )
        
        # 선택한 아이템의 순서 변경
        await prisma_client.productionQueue.update(
            where={"id": queue_id},
            data={"queue_order": new_order}
        )
        
        # 변경된 큐 조회
        updated_queue = await prisma_client.productionQueue.find_many(
            where={"city_id": city_id},
            orderBy={"queue_order": "asc"}
        )
        
        # 응답 데이터 변환
        result = []
        for item in updated_queue:
            # 아이템 이름 조회 (유닛 또는 건물)
            item_name = ""
            if item.itemType == "unit":
                unit_type = await prisma_client.unitType.find_unique(
                    where={"id": item.itemId}
                )
                item_name = unit_type.name if unit_type else item.itemId
            elif item.itemType == "building":
                building_type = await prisma_client.buildingType.find_unique(
                    where={"id": item.itemId}
                )
                item_name = building_type.name if building_type else item.itemId
            
            result.append({
                "id": item.id,
                "itemType": item.itemType,
                "itemId": item.itemId,
                "name": item_name,
                "turnsLeft": item.turns_left,
                "queueOrder": item.queue_order
            })
        
        return {
            "success": True,
            "message": "생산 아이템 순서가 변경되었습니다",
            "queue": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"생산 아이템 순서 변경 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"생산 아이템 순서 변경 중 오류 발생: {str(e)}"
        )

@router.delete("/{game_id}/city/{city_id}/production/{queue_id}")
async def delete_production_item(game_id: str, city_id: int, queue_id: int):
    """생산 큐 아이템 삭제 API"""
    try:
        # 도시 존재 확인
        city = await prisma_client.city.find_first(
            where={
                "session_id": game_id,
                "id": city_id
            }
        )
        
        if not city:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="도시를 찾을 수 없습니다"
            )
        
        # 큐 아이템 존재 확인
        queue_item = await prisma_client.productionQueue.find_unique(
            where={"id": queue_id}
        )
        
        if not queue_item or queue_item.city_id != city_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="생산 큐 아이템을 찾을 수 없습니다"
            )
        
        # 아이템 삭제
        await prisma_client.productionQueue.delete(
            where={"id": queue_id}
        )
        
        # 남은 아이템 순서 재조정
        await update_queue_order(city_id)
        
        # 변경된 큐 조회
        updated_queue = await prisma_client.productionQueue.find_many(
            where={"city_id": city_id},
            orderBy={"queue_order": "asc"}
        )
        
        # 응답 데이터 변환
        result = []
        for item in updated_queue:
            # 아이템 이름 조회 (유닛 또는 건물)
            item_name = ""
            if item.itemType == "unit":
                unit_type = await prisma_client.unitType.find_unique(
                    where={"id": item.itemId}
                )
                item_name = unit_type.name if unit_type else item.itemId
            elif item.itemType == "building":
                building_type = await prisma_client.buildingType.find_unique(
                    where={"id": item.itemId}
                )
                item_name = building_type.name if building_type else item.itemId
            
            result.append({
                "id": item.id,
                "itemType": item.itemType,
                "itemId": item.itemId,
                "name": item_name,
                "turnsLeft": item.turns_left,
                "queueOrder": item.queue_order
            })
        
        return {
            "success": True,
            "message": "생산 아이템이 삭제되었습니다",
            "queue": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"생산 아이템 삭제 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"생산 아이템 삭제 중 오류 발생: {str(e)}"
        )

@router.post("/{game_id}/city/{city_id}/specialize")
async def specialize_city(game_id: str, city_id: int, request: CitySpecializeRequest):
    """도시 특화 설정 API"""
    try:
        # 도시 존재 확인
        city = await prisma_client.city.find_first(
            where={
                "session_id": game_id,
                "id": city_id
            }
        )
        
        if not city:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="도시를 찾을 수 없습니다"
            )
        
        # 도시 특화 설정 업데이트
        specialization = request.specialization.value  # enum 값 추출
        
        updated_city = await prisma_client.city.update(
            where={"id": city_id},
            data={"specialization": specialization},
            include={
                "buildings": True,
                "production_queue": {
                    "orderBy": {
                        "queue_order": "asc"
                    }
                }
            }
        )
        
        # 특화에 따라 생산력 조정 (예시)
        production_bonus = 0
        if specialization == "production":
            production_bonus = 2
        
        # 도시 생산력 업데이트
        if production_bonus > 0:
            await prisma_client.city.update(
                where={"id": city_id},
                data={"production": updated_city.production + production_bonus}
            )
        
        return {
            "success": True,
            "message": f"도시 특화가 {specialization}으로 설정되었습니다",
            "specialization": specialization
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"도시 특화 설정 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"도시 특화 설정 중 오류 발생: {str(e)}"
        ) 