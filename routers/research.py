from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from core.config import prisma_client
from models.game import GameTurnInfo

router = APIRouter()

class TechTreeResponse(BaseModel):
    technologies: List[Dict[str, Any]]
    eras: List[str]

class ResearchStartRequest(BaseModel):
    game_id: str
    player_id: str
    tech_id: str

class ResearchStatusResponse(BaseModel):
    current_research: Optional[Dict[str, Any]] = None
    research_points: int
    completed_techs: List[Dict[str, Any]]
    available_techs: List[Dict[str, Any]]

class TechDetailResponse(BaseModel):
    id: str
    name: str
    era: Optional[str] = None
    cost: int
    description: Optional[str] = None
    prerequisites: List[Dict[str, Any]] = []
    unlocks: List[Dict[str, Any]] = []
    units: List[Dict[str, Any]] = []
    buildings: List[Dict[str, Any]] = []
    effects: Dict[str, Any] = {}

@router.get("/tech-tree", response_model=TechTreeResponse)
async def get_tech_tree(game_id: Optional[str] = None, player_id: Optional[str] = None):
    """
    기술 트리 조회 API
    
    game_id와 player_id가 제공되면 해당 게임의 연구 상태를 포함하여 반환
    그렇지 않으면 기본 트리 정보만 반환
    """
    try:
        # 모든 기술 정보 조회
        techs = await prisma_client.tech.find_many(
            include={
                "prerequisites": {
                    "include": {
                        "prereq": True
                    }
                },
                "dependents": {
                    "include": {
                        "tech": True
                    }
                }
            }
        )
        
        # 게임별 연구 상태 정보 (선택적)
        researched_techs = []
        current_research = None
        
        if game_id and player_id:
            # 해당 게임에서 이미 연구된 기술 목록
            researched = await prisma_client.researchedtech.find_many(
                where={
                    "game_id": game_id,
                    "player_id": player_id
                }
            )
            researched_techs = [rt.tech_id for rt in researched]
            
            # 현재 연구 중인 기술
            in_progress = await prisma_client.researchprogress.find_first(
                where={
                    "game_id": game_id,
                    "player_id": player_id,
                    "completed": False
                },
                include={
                    "tech": True
                }
            )
            
            if in_progress:
                current_research = {
                    "id": in_progress.tech_id,
                    "name": in_progress.tech.name,
                    "progress": in_progress.progress,
                    "cost": in_progress.tech.cost,
                    "turns_left": max(1, int((in_progress.tech.cost - in_progress.progress) / 3))  # 턴당 3 과학 포인트 예상
                }
        
        # 기술 데이터 가공
        tech_data = []
        eras = set()
        
        for tech in techs:
            
            # 시대 정보 수집
            if tech.era:
                eras.add(tech.era)
            
            tech_info = {
                "id": tech.id,
                "name": tech.name,
                "era": tech.era,
                "cost": tech.cost,
                "description": tech.description,
                "prerequisites": [p.prereqId for p in tech.prerequisites],
                "unlocks": [d.techId for d in tech.dependents],
                "is_researched": tech.id in researched_techs,
                "is_current": current_research and current_research["id"] == tech.id
            }
            
            tech_data.append(tech_info)
        
        return {
            "technologies": tech_data,
            "eras": sorted(list(eras))
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"기술 트리 조회 중 오류 발생: {str(e)}"
        )

@router.get("/available", response_model=List[Dict[str, Any]])
async def get_available_techs(game_id: str, player_id: str):
    """
    연구 가능한 기술 목록 조회 API
    
    선행 기술이 모두 연구되었고, 아직 연구하지 않은 기술 목록 반환
    """
    try:
        # 이미 연구한 기술 ID 목록
        researched = await prisma_client.researchedtech.find_many(
            where={
                "game_id": game_id,
                "player_id": player_id
            }
        )
        researched_tech_ids = [rt.tech_id for rt in researched]
        
        # 현재 연구 중인 기술 확인
        in_progress = await prisma_client.researchprogress.find_first(
            where={
                "game_id": game_id,
                "player_id": player_id,
                "completed": False
            }
        )
        
        # 모든 기술과 선행 조건 조회
        all_techs = await prisma_client.tech.find_many(
            include={
                "prerequisites": True
            }
        )
        
        # 선행 기술이 모두 연구된 기술만 필터링
        available_techs = []
        
        for tech in all_techs:
            # 이미 연구했거나 연구 중인 기술 제외
            if tech.id in researched_tech_ids or (in_progress and in_progress.tech_id == tech.id):
                continue
            
            # 선행 기술이 없는 경우 바로 연구 가능
            if not tech.prerequisites:
                available_techs.append({
                    "id": tech.id,
                    "name": tech.name,
                    "era": tech.era,
                    "cost": tech.cost,
                    "description": tech.description
                })
                continue
            
            # 모든 선행 기술이 연구되었는지 확인
            all_prereqs_researched = True
            for prereq in tech.prerequisites:
                if prereq.prereq_id not in researched_tech_ids:
                    all_prereqs_researched = False
                    break
            
            if all_prereqs_researched:
                available_techs.append({
                    "id": tech.id,
                    "name": tech.name,
                    "era": tech.era,
                    "cost": tech.cost,
                    "description": tech.description
                })
        
        return available_techs
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"연구 가능한 기술 조회 중 오류 발생: {str(e)}"
        )

@router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_research(request: ResearchStartRequest):
    """
    기술 연구 시작 API
    
    선행 기술이 모두 연구되었는지 확인 후, 연구 진행 상태를 생성
    """
    try:
        # GameResearch 정보 조회
        game_research = await prisma_client.gameresearch.find_unique(
            where={
                "session_id": request.game_id
            }
        )
        
        # 기존에 연구 중인 기술이 있는지 확인
        if game_research and game_research.current_tech_id:
            tech = await prisma_client.tech.find_unique(
                where={"id": game_research.current_tech_id}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"다른 기술('{tech.name}')이 이미 연구 중입니다."
            )
        
        # 연구하려는 기술 정보 확인
        tech = await prisma_client.tech.find_unique(
            where={"id": request.tech_id},
            include={
                "prerequisites": True
            }
        )
        
        if not tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 기술입니다."
            )
        
        # 이미 연구한 기술인지 확인
        already_researched = await prisma_client.researchedtech.find_unique(
            where={
                "session_id_tech_id": {
                    "session_id": request.game_id,
                    "tech_id": request.tech_id
                }
            }
        )
        
        if already_researched:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 연구 완료된 기술입니다."
            )
        
        # 선행 기술 모두 연구되었는지 확인
        if tech.prerequisites:
            for prereq in tech.prerequisites:
                prereq_researched = await prisma_client.researchedtech.find_unique(
                    where={
                        "session_id_tech_id": {
                            "session_id": request.game_id,
                            "tech_id": prereq.prereqId
                        }
                    }
                )
                
                if not prereq_researched:
                    # 해당 선행 기술 정보 조회
                    missing_prereq = await prisma_client.tech.find_unique(
                        where={"id": prereq.prereqId}
                    )
                    
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"선행 기술 '{missing_prereq.name}'을(를) 먼저 연구해야 합니다."
                    )
        
        # 플레이어 정보 조회
        player = await prisma_client.player.find_first(
            where={
                "id": int(request.player_id),
                "session_id": request.game_id
            }
        )
        
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="플레이어 정보를 찾을 수 없습니다."
            )
        
        # GameResearch가 없으면 생성
        if not game_research:
            game_research = await prisma_client.gameresearch.create(
                data={
                    "session_id": request.game_id,
                    "current_tech_id": request.tech_id
                }
            )
        else:
            # 기존 GameResearch 업데이트
            game_research = await prisma_client.gameresearch.update(
                where={
                    "session_id": request.game_id
                },
                data={
                    "current_tech_id": request.tech_id
                }
            )
        
        # 연구 진행 상태 생성
        research_progress = await prisma_client.researchprogress.create(
            data={
                "session_id": request.game_id,
                "tech_id": request.tech_id,
                "progress": 0
            }
        )
        
        return {
            "message": f"'{tech.name}' 기술 연구를 시작했습니다.",
            "tech_id": request.tech_id,
            "tech_name": tech.name,
            "cost": tech.cost,
            "research_id": f"{request.game_id}_{request.tech_id}"  # 복합키 대신 식별자 생성
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"연구 시작 중 오류 발생: {str(e)}"
        )

@router.get("/status/{game_id}/{player_id}", response_model=ResearchStatusResponse)
async def get_research_status(game_id: str, player_id: str):
    """
    연구 현황 조회 API
    
    현재 연구 중인 기술, 연구 완료된 기술, 연구 가능한 기술 목록 반환
    """
    try:
        # 현재 연구 중인 기술
        current_research = None
        
        # GameResearch 정보 조회
        game_research = await prisma_client.gameresearch.find_unique(
            where={
                "session_id": game_id
            },
            include={
                "current_tech": True
            }
        )
        
        if game_research and game_research.current_tech_id:
            # 현재 연구 중인 기술의 진행 상태 확인
            research_progress = await prisma_client.researchprogress.find_unique(
                where={
                    "session_id_tech_id": {
                        "session_id": game_id,
                        "tech_id": game_research.current_tech_id
                    }
                }
            )
            
            if research_progress:
                # 플레이어의 과학 생산량 조회 (도시 합계)
                cities = await prisma_client.city.find_many(
                    where={
                        "session_id": game_id,
                        "owner_player_id": int(player_id)
                    }
                )
                
                science_per_turn = sum(city.science for city in cities) if cities else 3  # 기본값 3
                turns_left = max(1, int((game_research.current_tech.cost - research_progress.progress) / science_per_turn))
                
                current_research = {
                    "id": game_research.current_tech_id,
                    "name": game_research.current_tech.name,
                    "era": game_research.current_tech.era,
                    "progress": research_progress.progress,
                    "cost": game_research.current_tech.cost,
                    "percent": min(100, int((research_progress.progress / game_research.current_tech.cost) * 100)),
                    "turns_left": turns_left,
                    "science_per_turn": science_per_turn
                }
        
        # 연구 완료된 기술 목록
        completed_techs = []
        researched = await prisma_client.researchedtech.find_many(
            where={
                "session_id": game_id
            },
            include={
                "tech": True
            }
        )
        
        if researched:
            completed_techs = [
                {
                    "id": item.tech_id,
                    "name": item.tech.name,
                    "era": item.tech.era,
                    "completed_at": getattr(item, "completed_at", None)  # 필드가 있으면 사용, 없으면 None
                }
                for item in researched
            ]
        
        # 연구 가능한 기술 목록 (선행 기술이 모두 연구된 기술)
        completed_tech_ids = [ct["id"] for ct in completed_techs]
        
        all_techs = await prisma_client.tech.find_many(
            include={
                "prerequisites": True
            }
        )
        
        available_techs = []
        current_tech_id = game_research.current_tech_id if game_research else None
        
        for tech in all_techs:
            # 이미 연구했거나 연구 중인 기술은 제외
            if tech.id in completed_tech_ids or tech.id == current_tech_id:
                continue
            
            # 선행 기술이 없는 경우 바로 연구 가능
            if not tech.prerequisites:
                available_techs.append({
                    "id": tech.id,
                    "name": tech.name,
                    "era": tech.era,
                    "cost": tech.cost
                })
                continue
            
            # 모든 선행 기술이 연구되었는지 확인
            all_prereqs_researched = True
            for prereq in tech.prerequisites:
                if prereq.prereqId not in completed_tech_ids:
                    all_prereqs_researched = False
                    break
            
            if all_prereqs_researched:
                available_techs.append({
                    "id": tech.id,
                    "name": tech.name,
                    "era": tech.era,
                    "cost": tech.cost
                })
        
        # 플레이어 과학 생산량 계산
        cities = await prisma_client.city.find_many(
            where={
                "session_id": game_id,
                "owner_player_id": int(player_id)
            }
        )
        
        research_points = sum(city.science for city in cities) if cities else 3
        
        return {
            "current_research": current_research,
            "research_points": research_points,
            "completed_techs": completed_techs,
            "available_techs": available_techs
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"연구 상태 조회 중 오류 발생: {str(e)}"
        )

@router.put("/cancel")
async def cancel_research(game_id: str, player_id: str):
    """
    연구 취소 API
    
    현재 진행 중인 연구를 취소하고 진행 상태를 삭제
    """
    try:
        # 현재 연구 중인 기술 조회
        game_research = await prisma_client.gameresearch.find_unique(
            where={
                "session_id": game_id
            },
            include={
                "current_tech": True
            }
        )
        
        if not game_research or not game_research.current_tech_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="진행 중인 연구가 없습니다."
            )
        
        current_tech = game_research.current_tech
        current_tech_id = game_research.current_tech_id
        
        # 연구 진행 기록 삭제
        await prisma_client.researchprogress.delete(
            where={
                "session_id_tech_id": {
                    "session_id": game_id,
                    "tech_id": current_tech_id
                }
            }
        )
        
        # GameResearch 업데이트 (current_tech_id 제거)
        await prisma_client.gameresearch.update(
            where={
                "session_id": game_id
            },
            data={
                "current_tech_id": None
            }
        )
        
        return {
            "message": f"'{current_tech.name}' 기술 연구가 취소되었습니다.",
            "tech_id": current_tech_id,
            "tech_name": current_tech.name
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"연구 취소 중 오류 발생: {str(e)}"
        )

@router.put("/change")
async def change_research(game_id: str, player_id: str, new_tech_id: str):
    """
    연구 변경 API
    
    현재 진행 중인 연구를 취소하고 새로운 기술 연구 시작
    """
    try:
        # 현재 연구 중인 기술 조회
        game_research = await prisma_client.gameresearch.find_unique(
            where={
                "session_id": game_id
            }
        )
        
        # 새로 연구할 기술 정보 확인
        tech = await prisma_client.tech.find_unique(
            where={"id": new_tech_id},
            include={
                "prerequisites": True
            }
        )
        
        if not tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 기술입니다."
            )
        
        # 이미 연구한 기술인지 확인
        already_researched = await prisma_client.researchedtech.find_unique(
            where={
                "session_id_tech_id": {
                    "session_id": game_id,
                    "tech_id": new_tech_id
                }
            }
        )
        
        if already_researched:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 연구 완료된 기술입니다."
            )
        
        # 선행 기술 모두 연구되었는지 확인
        if tech.prerequisites:
            for prereq in tech.prerequisites:
                prereq_researched = await prisma_client.researchedtech.find_unique(
                    where={
                        "session_id_tech_id": {
                            "session_id": game_id,
                            "tech_id": prereq.prereqId
                        }
                    }
                )
                
                if not prereq_researched:
                    # 해당 선행 기술 정보 조회
                    missing_prereq = await prisma_client.tech.find_unique(
                        where={"id": prereq.prereqId}
                    )
                    
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"선행 기술 '{missing_prereq.name}'을(를) 먼저 연구해야 합니다."
                    )
        
        # 기존 연구 진행 정보가 있으면 삭제
        if game_research and game_research.current_tech_id:
            # 기존 연구 진행 상태 삭제
            try:
                await prisma_client.researchprogress.delete(
                    where={
                        "session_id_tech_id": {
                            "session_id": game_id,
                            "tech_id": game_research.current_tech_id
                        }
                    }
                )
            except Exception as e:
                print(f"기존 연구 삭제 실패: {str(e)}")
                pass  # 없을 수도 있으므로 오류 무시
        
        # GameResearch 업데이트
        if game_research:
            game_research = await prisma_client.gameresearch.update(
                where={
                    "session_id": game_id
                },
                data={
                    "current_tech_id": new_tech_id
                }
            )
        else:
            # 없으면 새로 생성
            game_research = await prisma_client.gameresearch.create(
                data={
                    "session_id": game_id,
                    "current_tech_id": new_tech_id
                }
            )
        
        # 새 연구 진행 상태 생성
        research_progress = await prisma_client.researchprogress.create(
            data={
                "session_id": game_id,
                "tech_id": new_tech_id,
                "progress": 0
            }
        )
        
        return {
            "message": f"연구 주제를 '{tech.name}'(으)로 변경했습니다.",
            "tech_id": new_tech_id,
            "tech_name": tech.name,
            "cost": tech.cost,
            "research_id": f"{game_id}_{new_tech_id}"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"연구 변경 중 오류 발생: {str(e)}"
        )

@router.get("/tech/{tech_id}", response_model=TechDetailResponse)
async def get_tech_detail(tech_id: str):
    """
    특정 기술의 상세 정보 조회 API
    
    기술 ID에 해당하는 기술의 상세 정보, 선행 기술, 잠금 해제 항목 등을 반환
    """
    try:
        # 기술 기본 정보 조회
        tech = await prisma_client.tech.find_unique(
            where={"id": tech_id},
            include={
                "prerequisites": {
                    "include": {
                        "prereq": True
                    }
                },
                "dependents": {
                    "include": {
                        "tech": True
                    }
                }
            }
        )
        
        if not tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"기술 ID '{tech_id}'에 해당하는 기술을 찾을 수 없습니다."
            )
        
        # 이 기술이 언락하는 유닛 목록 조회
        unlocked_units = await prisma_client.unittype.find_many(
            where={
                "required_tech_id": tech_id
            }
        )
        
        # 이 기술이 언락하는 건물 목록 조회
        unlocked_buildings = await prisma_client.buildingtype.find_many(
            where={
                "required_tech_id": tech_id
            }
        )
        
        # 선택된 필드만 포함하여 반환
        unit_data = [
            {
                "id": unit.id,
                "name": unit.name,
                "combat_type": getattr(unit, "combat_type", None),
                "combat_strength": getattr(unit, "combat_strength", None)
            }
            for unit in unlocked_units
        ]
        
        building_data = [
            {
                "id": building.id,
                "name": building.name,
                "production_cost": getattr(building, "production_cost", None),
                "effects": getattr(building, "effects", {})
            }
            for building in unlocked_buildings
        ]
        
        # 선행 기술 정보
        prerequisites = []
        for prereq in tech.prerequisites:
            if hasattr(prereq, 'prereq') and prereq.prereq:
                prerequisites.append({
                    "id": prereq.prereq.id,
                    "name": prereq.prereq.name,
                    "era": prereq.prereq.era
                })
            elif hasattr(prereq, 'prereqId'):
                # prereqId만 있는 경우 기본 정보만 포함
                prerequisites.append({
                    "id": prereq.prereqId,
                    "name": prereq.prereqId  # ID만 표시
                })
        
        # 이 기술 이후에 연구할 수 있는 기술들
        unlocks_techs = []
        for dependent in tech.dependents:
            if hasattr(dependent, 'tech') and dependent.tech:
                unlocks_techs.append({
                    "id": dependent.tech.id,
                    "name": dependent.tech.name,
                    "era": dependent.tech.era
                })
            elif hasattr(dependent, 'techId'):
                # techId만 있는 경우 기본 정보만 포함
                unlocks_techs.append({
                    "id": dependent.techId,
                    "name": dependent.techId  # ID만 표시
                })
        
        # 기술 효과 정보 (DB에서 가져오거나 하드코딩)
        effects = {}
        
        # 시대별 특수 효과 추가
        if tech.era == "고대":
            effects["science_bonus"] = 0
        elif tech.era == "중세":
            effects["science_bonus"] = 1
        elif tech.era == "르네상스":
            effects["science_bonus"] = 2
        elif tech.era == "산업":
            effects["science_bonus"] = 3
        elif tech.era == "근대":
            effects["science_bonus"] = 4
        elif tech.era == "원자":
            effects["science_bonus"] = 5
        
        # 특정 기술별 효과 (예시)
        if tech_id == "writing":
            effects["enables_diplomacy"] = True
        elif tech_id == "currency":
            effects["trade_route_bonus"] = 25
        elif tech_id == "flight":
            effects["movement_bonus"] = 1
            
        # 응답 구성
        response = {
            "id": tech.id,
            "name": tech.name,
            "era": tech.era,
            "cost": tech.cost,
            "description": tech.description,
            "prerequisites": prerequisites,
            "unlocks": unlocks_techs,
            "units": unit_data,
            "buildings": building_data,
            "effects": effects
        }
        
        return response
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"기술 상세 정보 조회 중 오류 발생: {str(e)}"
        ) 