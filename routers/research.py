from fastapi import APIRouter, HTTPException, Query, Body, Path
from typing import List, Optional, Dict, Any
from enum import Enum
from db.client import prisma
from pydantic import BaseModel

router = APIRouter()

class EraType(str, Enum):
    Medieval = "Medieval"
    Industrial = "Industrial"
    Modern = "Modern"

class TreeType(str, Enum):
    military = "military"
    defense = "defense"
    economic = "economic"
    science = "science"
    diplomacy = "diplomacy"

class ResearchStartRequest(BaseModel):
    techId: int

class TreeSelectionRequest(BaseModel):
    main: TreeType
    sub: Optional[TreeType] = None

class UnitCategory(str, Enum):
    Melee = "Melee"
    Ranged = "Ranged"
    Cavalry = "Cavalry"
    Siege = "Siege"
    Modern = "Modern"
    Civilian = "Civilian"

@router.get("/", summary="기술 목록 조회", response_description="기술 목록 반환")
async def get_technologies(
    era: Optional[EraType] = None,
    treeType: Optional[TreeType] = None,
    available: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """기술 목록을 조회합니다."""
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
        
        if treeType:
            where_condition["treeType"] = treeType.value
        
        # 가용 기술 필터링은 별도로 처리해야 함 (아래에서 DB 쿼리 후)
        
        # 기술 목록 조회
        technologies = await prisma.technology.find_many(
            where=where_condition,
            skip=offset,
            take=limit
        )
        
        # 결과 변환
        result = []
        for tech in technologies:
            result.append({
                "id": tech.id,
                "name": tech.name,
                "description": tech.description,
                "era": tech.era,
                "treeType": tech.treeType,
                "researchCost": tech.researchCost,
                "researchTimeModifier": tech.researchTimeModifier
            })
        
        # available 필터링은 구현이 복잡하므로 이 부분은 실제 구현 시 확장 필요
        
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

@router.get("/{tech_id}", summary="기술 상세 조회", response_description="기술 상세 정보 반환")
async def get_technology_detail(tech_id: int):
    """특정 기술의 상세 정보를 조회합니다."""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 기술 조회
        tech = await prisma.technology.find_unique(
            where={"id": tech_id}
        )
        
        if not tech:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "NotFoundError",
                    "detail": f"ID가 {tech_id}인 기술을 찾을 수 없습니다."
                }
            }
        
        # 결과 변환
        result = {
            "id": tech.id,
            "name": tech.name,
            "description": tech.description,
            "era": tech.era,
            "treeType": tech.treeType,
            "researchCost": tech.researchCost,
            "researchTimeModifier": tech.researchTimeModifier
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

@router.get("/game-civs/{game_civ_id}/research-status", summary="연구 상태 조회", response_description="문명별 연구 상태 반환")
async def get_research_status(game_civ_id: int = Path(..., description="문명 인스턴스 ID")):
    """한 문명의 전체 연구 현황(완료·진행중·가능)을 조회합니다."""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 연구 완료된 기술 조회
        completed_techs = await prisma.gamecivtechnology.find_many(
            where={
                "gameCivId": game_civ_id,
                "status": "completed"
            }
        )
        
        # 연구 중인 기술 조회
        in_progress_tech = await prisma.gamecivtechnology.find_first(
            where={
                "gameCivId": game_civ_id,
                "status": "in_progress"
            }
        )
        
        # 완료된 기술 ID 목록
        completed_tech_ids = [tech.techId for tech in completed_techs]
        
        # 선택된 트리 조회
        tree_selections = await prisma.treeselection.find_many(
            where={
                "gameCivId": game_civ_id
            }
        )
        
        # 선택된 기술 트리 식별
        selected_tree_types = []
        for tree in tree_selections:
            selected_tree_types.append(tree.treeType)
        
        # 모든 기술 조회
        all_techs = await prisma.technology.find_many()
        
        # 가용 기술 (완료되지 않은 기술 중 선행 기술 요구사항을 충족하는 것)
        available_tech_ids = []
        for tech in all_techs:
            # 이미 완료된 기술은 제외
            if tech.id in completed_tech_ids:
                continue
                
            # 진행 중인 기술도 제외
            if in_progress_tech and tech.id == in_progress_tech.techId:
                continue
                
            # 선택된 트리에 해당하는 기술만 포함 (메인 또는 서브)
            if tech.treeType not in selected_tree_types:
                continue
                
            # 선행 기술 확인
            is_available = True
            
            # prerequisiteId가 있으면 확인 (없으면 시작 기술로 간주)
            if hasattr(tech, 'prerequisiteId') and tech.prerequisiteId is not None:
                if tech.prerequisiteId not in completed_tech_ids:
                    is_available = False
            
            if is_available:
                available_tech_ids.append(tech.id)
        
        # 연구 진행 상태 구성
        in_progress_data = None
        if in_progress_tech:
            # 해당 기술의 총 연구 비용 조회
            tech_details = await prisma.technology.find_unique(
                where={"id": in_progress_tech.techId}
            )
            
            in_progress_data = {
                "techId": in_progress_tech.techId,
                "points": in_progress_tech.progressPoints,
                "required": tech_details.researchCost
            }
        
        result = {
            "completed": completed_tech_ids,
            "inProgress": in_progress_data,
            "available": available_tech_ids
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

@router.get("/game-civs/{game_civ_id}/research-queue", summary="연구 큐 조회", response_description="연구 예약 목록 반환")
async def get_research_queue(game_civ_id: int = Path(..., description="문명 인스턴스 ID")):
    """연구 예약 큐를 조회합니다."""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 연구 큐 조회
        queue_entries = await prisma.researchqueue.find_many(
            where={
                "gameCivId": game_civ_id
            }
        )
        
        # 결과 변환 및 수동 정렬
        result = sorted([
            {
                "queueId": entry.id,
                "techId": entry.techId,
                "queuePosition": entry.queuePosition
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

@router.post("/game-civs/{game_civ_id}/research-queue", summary="연구 큐 추가", response_description="연구 예약 추가 결과")
async def add_to_research_queue(
    tech_request: Dict[str, int] = Body(..., example={"techId": 8}),
    game_civ_id: int = Path(..., description="문명 인스턴스 ID")
):
    """새로운 기술을 연구 큐에 추가합니다."""
    try:
        tech_id = tech_request.get("techId")
        if not tech_id:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "ValidationError",
                    "detail": "유효한 techId를 제공해야 합니다."
                }
            }
        
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 현재 큐 크기 확인
        current_queue = await prisma.researchqueue.find_many(
            where={
                "gameCivId": game_civ_id
            }
        )
        
        if len(current_queue) >= 3:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "QueueFullError",
                    "detail": "연구 큐가 꽉 찼습니다 (최대 3개)."
                }
            }
        
        # 새 큐 위치 계산
        next_position = 1
        if current_queue:
            next_position = max(entry.queuePosition for entry in current_queue) + 1
        
        # 연구 큐에 추가
        new_queue_entry = await prisma.researchqueue.create(
            data={
                "gameCivId": game_civ_id,
                "techId": tech_id,
                "queuePosition": next_position,
                "addedAt": prisma.datetime.now()
            }
        )
        
        result = {
            "queueId": new_queue_entry.id,
            "techId": new_queue_entry.techId,
            "queuePosition": new_queue_entry.queuePosition
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

@router.delete("/game-civs/{game_civ_id}/research-queue/{queue_id}", summary="연구 큐 제거", response_description="연구 예약 취소 결과")
async def remove_from_research_queue(
    game_civ_id: int = Path(..., description="문명 인스턴스 ID"),
    queue_id: int = Path(..., description="큐 엔트리 ID")
):
    """연구 큐에서 기술을 제거합니다."""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 큐 엔트리 확인
        queue_entry = await prisma.researchqueue.find_unique(
            where={
                "id": queue_id
            }
        )
        
        if not queue_entry or queue_entry.gameCivId != game_civ_id:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "NotFoundError",
                    "detail": f"ID가 {queue_id}인 큐 엔트리를 찾을 수 없거나 접근 권한이 없습니다."
                }
            }
        
        # 제거할 큐 엔트리의 위치 저장
        removed_position = queue_entry.queuePosition
        
        # 큐 엔트리 제거
        await prisma.researchqueue.delete(
            where={
                "id": queue_id
            }
        )
        
        # 다른 큐 엔트리의 위치 재조정
        await prisma.researchqueue.update_many(
            where={
                "gameCivId": game_civ_id,
                "queuePosition": {
                    "gt": removed_position
                }
            },
            data={
                "queuePosition": {
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

@router.post("/game-civs/{game_civ_id}/research/start", summary="연구 시작", response_description="연구 시작 결과")
async def start_research(
    tech_request: Dict[str, int] = Body(..., example={"techId": 9}),
    game_civ_id: int = Path(..., description="문명 인스턴스 ID")
):
    """특정 기술의 연구를 직접 시작합니다."""
    try:
        tech_id = tech_request.get("techId")
        if not tech_id:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "ValidationError",
                    "detail": "유효한 techId를 제공해야 합니다."
                }
            }
        
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 이미 연구 중인 기술이 있는지 확인
        in_progress = await prisma.gamecivtechnology.find_first(
            where={
                "gameCivId": game_civ_id,
                "status": "in_progress"
            }
        )
        
        if in_progress:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "ConflictError",
                    "detail": f"이미 연구 중인 기술이 있습니다 (ID: {in_progress.techId})."
                }
            }
        
        # 기술 정보 조회
        tech = await prisma.technology.find_unique(
            where={"id": tech_id}
        )
        
        if not tech:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "NotFoundError",
                    "detail": f"ID가 {tech_id}인 기술을 찾을 수 없습니다."
                }
            }
        
        # 이미 완료된 기술인지 확인
        completed = await prisma.gamecivtechnology.find_first(
            where={
                "gameCivId": game_civ_id,
                "techId": tech_id,
                "status": "completed"
            }
        )
        
        if completed:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "ConflictError",
                    "detail": f"이미 완료된 기술입니다 (ID: {tech_id})."
                }
            }
        
        # 연구 시작 (또는 기존 레코드 업데이트)
        existing_record = await prisma.gamecivtechnology.find_first(
            where={
                "gameCivId": game_civ_id,
                "techId": tech_id
            }
        )
        
        research_record = None
        
        if existing_record:
            # 기존 레코드 업데이트
            research_record = await prisma.gamecivtechnology.update(
                where={"id": existing_record.id},
                data={
                    "status": "in_progress",
                    "startedAt": prisma.datetime.now()
                }
            )
        else:
            # 새 레코드 생성
            research_record = await prisma.gamecivtechnology.create(
                data={
                    "gameCivId": game_civ_id,
                    "techId": tech_id,
                    "status": "in_progress",
                    "progressPoints": 0,
                    "startedAt": prisma.datetime.now()
                }
            )
        
        result = {
            "techId": tech_id,
            "status": "in_progress",
            "points": research_record.progressPoints,
            "required": tech.researchCost
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

@router.post("/game-civs/{game_civ_id}/research/cancel", summary="연구 취소", response_description="연구 취소 결과")
async def cancel_research(
    tech_request: Dict[str, int] = Body(..., example={"techId": 9}),
    game_civ_id: int = Path(..., description="문명 인스턴스 ID")
):
    """진행 중인 기술 연구를 취소합니다."""
    try:
        tech_id = tech_request.get("techId")
        if not tech_id:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "ValidationError",
                    "detail": "유효한 techId를 제공해야 합니다."
                }
            }
        
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 연구 중인 기술 찾기
        research_record = await prisma.gamecivtechnology.find_first(
            where={
                "gameCivId": game_civ_id,
                "techId": tech_id,
                "status": "in_progress"
            }
        )
        
        if not research_record:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "NotFoundError",
                    "detail": f"현재 연구 중인 기술 (ID: {tech_id})을 찾을 수 없습니다."
                }
            }
        
        # 연구 상태 업데이트 (available 상태로)
        await prisma.gamecivtechnology.update(
            where={"id": research_record.id},
            data={
                "status": "available",
                "startedAt": None
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

@router.get("/game-civs/{game_civ_id}/tree-selection", summary="기술 트리 선택 조회", response_description="선택된 기술 트리 반환")
async def get_tree_selection(game_civ_id: int = Path(..., description="문명 인스턴스 ID")):
    """문명의 현재 선택된 기술 트리를 조회합니다."""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 선택된 트리 조회
        tree_selections = await prisma.treeselection.find_many(
            where={
                "gameCivId": game_civ_id
            }
        )
        
        # 결과 변환
        main_tree = None
        sub_tree = None
        
        for tree in tree_selections:
            if tree.isMain:
                main_tree = tree.treeType
            else:
                sub_tree = tree.treeType
        
        result = {
            "main": main_tree,
            "sub": sub_tree
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

@router.post("/game-civs/{game_civ_id}/tree-selection", summary="기술 트리 선택", response_description="기술 트리 선택 결과")
async def set_tree_selection(
    selection: TreeSelectionRequest,
    game_civ_id: int = Path(..., description="문명 인스턴스 ID")
):
    """문명의 기술 트리를 선택합니다."""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 기존 선택 조회
        existing_selections = await prisma.treeselection.find_many(
            where={
                "gameCivId": game_civ_id
            }
        )
        
        # 메인 트리 처리
        main_tree_exists = False
        for tree in existing_selections:
            if tree.isMain:
                # 메인 트리 업데이트
                await prisma.treeselection.update(
                    where={"id": tree.id},
                    data={
                        "treeType": selection.main,
                        "selectedAt": prisma.datetime.now()
                    }
                )
                main_tree_exists = True
                break
        
        if not main_tree_exists:
            # 새 메인 트리 생성
            await prisma.treeselection.create(
                data={
                    "gameCivId": game_civ_id,
                    "treeType": selection.main,
                    "isMain": True,
                    "selectedAt": prisma.datetime.now()
                }
            )
        
        # 보조 트리 처리
        if selection.sub:
            sub_tree_exists = False
            for tree in existing_selections:
                if not tree.isMain:
                    # 보조 트리 업데이트
                    await prisma.treeselection.update(
                        where={"id": tree.id},
                        data={
                            "treeType": selection.sub,
                            "selectedAt": prisma.datetime.now()
                        }
                    )
                    sub_tree_exists = True
                    break
            
            if not sub_tree_exists:
                # 새 보조 트리 생성
                await prisma.treeselection.create(
                    data={
                        "gameCivId": game_civ_id,
                        "treeType": selection.sub,
                        "isMain": False,
                        "selectedAt": prisma.datetime.now()
                    }
                )
        elif len(existing_selections) > 1:
            # 보조 트리 선택을 해제한 경우, 기존 보조 트리 삭제
            for tree in existing_selections:
                if not tree.isMain:
                    await prisma.treeselection.delete(
                        where={"id": tree.id}
                    )
        
        result = {
            "main": selection.main,
            "sub": selection.sub
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
