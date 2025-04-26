from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class TerrainType(str, Enum):
    """지형 타입 열거형"""
    PLAINS = "평지"
    GRASSLAND = "초원"
    HILLS = "언덕"
    FOREST = "숲"
    DESERT = "사막"
    MOUNTAIN = "산악"
    OCEAN = "바다"
    COAST = "해안"

class ResourceType(str, Enum):
    """자원 타입 열거형"""
    WHEAT = "식량"
    HORSES = "말"
    CATTLE = "소"
    SHEEP = "양"
    IRON = "철"
    COAL = "석탄"
    GOLD = "금"
    FISH = "물고기"

class HexCoord(BaseModel):
    """육각형 좌표 모델"""
    q: int = Field(..., description="육각형 Q 좌표")
    r: int = Field(..., description="육각형 R 좌표")
    s: int = Field(..., description="육각형 S 좌표 (Q + R + S = 0)")

    def __init__(self, **data):
        super().__init__(**data)
        if "s" not in data:
            self.s = -self.q - self.r

class HexTile(BaseModel):
    """육각형 타일 모델"""
    q: int = Field(..., description="육각형 Q 좌표")
    r: int = Field(..., description="육각형 R 좌표")
    s: int = Field(..., description="육각형 S 좌표")
    terrain: TerrainType = Field(..., description="지형 타입")
    resource: Optional[ResourceType] = Field(None, description="자원 타입")
    visible: bool = Field(False, description="시야 범위 내 보이는지 여부")
    explored: bool = Field(False, description="탐험 여부")
    city_id: Optional[str] = Field(None, description="도시 ID")
    unit_id: Optional[str] = Field(None, description="유닛 ID")
    occupant: Optional[str] = Field(None, description="점령 문명")

    def __init__(self, **data):
        super().__init__(**data)
        if "s" not in data:
            self.s = -self.q - self.r

class Civilization(BaseModel):
    """문명 모델"""
    name: str = Field(..., description="문명 이름")
    leader_name: str = Field(..., description="지도자 이름")
    personality: str = Field(..., description="문명 성격")
    cities: List[str] = Field(default_factory=list, description="도시 ID 목록")
    units: List[str] = Field(default_factory=list, description="유닛 ID 목록")
    resources: Dict[str, int] = Field(default_factory=dict, description="자원 보유량")
    technologies: List[str] = Field(default_factory=list, description="보유 기술 목록")

class GameMapState(BaseModel):
    """게임 맵 상태 모델"""
    game_id: str = Field(..., description="게임 ID")
    turn: int = Field(..., description="현재 턴")
    map_radius: int = Field(..., description="맵 반경")
    tiles: List[HexTile] = Field(..., description="육각형 타일 목록")
    civilizations: Dict[str, Civilization] = Field(..., description="문명 정보")
    player_civ_id: str = Field(..., description="플레이어 문명 ID")
    turn_limit: int = Field(..., description="최대 턴 수") 