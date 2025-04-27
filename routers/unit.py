from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from db.client import prisma
from enum import Enum

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