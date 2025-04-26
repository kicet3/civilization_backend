import uuid
import random
import time
import math
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any, Set, Tuple
from prisma.models import GameSession, Player, Hexagon, City, Unit, UnitType, Terrain, Resource
from models.game import GameSessionCreate, GameSessionResponse, GameState, GameOptions, GameOptionsResponse, TurnEndRequest, TurnEndResponse, GameTurnInfo, GameSpeed, GamePhase
from models.map import MapType, Difficulty
from core.config import prisma_client, settings
import json
from models.unit import UnitMoveRequest, UnitResponse
from utils.turn_manager import process_turn_end
from utils.scenario_manager import calculate_turn_year
from routers.websocket import manager as ws_manager
from utils.map_utils import (
    assign_guaranteed_resources, 
    distribute_map_resources, 
    setup_capital_yield, 
    create_starting_units,
    get_suggested_improvements
)

router = APIRouter()

# 헥스 좌표 저장을 위한 튜플 타입
HexCoord = Tuple[int, int, int]
import hashlib

def generate_deterministic_seed(mode, difficulty, civ, map_type, civ_count):

    # 모든 입력 파라미터를 문자열로 결합
    seed_input = f"{mode}_{difficulty}_{civ}_{map_type}_{civ_count}"
    
    # SHA-256 해시를 사용하여 고유한 정수 시드 생성
    hash_object = hashlib.sha256(seed_input.encode())
    
    # 해시의 처음 8바이트를 사용하여 큰 정수 생성
    seed_int = int.from_bytes(hash_object.digest()[:8], byteorder='big')
    
    return seed_int


async def create_initial_city(game_session_id: str, player_id: int, start_hex: Hexagon, civ: str):
    """플레이어 초기 도시 생성"""
    # 문명별 초기 도시 이름 결정
    civ_city_names = {
        "korea": "서울",
        "japan": "도쿄",
        "china": "베이징",
        "mongol": "카라코룸",
        "india": "델리",
        "england": "런던",
        "france": "파리",
        "germany": "베를린",
        "rome": "로마",
        "america": "워싱턴"
    }
    
    city_name = civ_city_names.get(civ, "수도")
    
    # City 스키마에 맞게 데이터 생성 - 위치 정보 필드 추가
    city = await prisma_client.city.create(
        data={
            "session_id": game_session_id,
            "name": city_name,
            "owner_player_id": player_id,
            "population": 1,
            "hp": 100,
            "defense": 10,
            "food": 5,
            "production": 3,
            "gold": 10,
            "science": 2,
            "culture": 1,
            "faith": 1,
            "happiness": 10,
            "food_to_next_pop": 10,
            "culture_to_next_border": 20,
            # 위치 정보 추가
            "loc_q": start_hex.q,
            "loc_r": start_hex.r,
            "loc_s": start_hex.s
        }
    )
    
    # 도시와 타일의 연결을 별도로 처리
    # 도시가 위치한 타일 업데이트 (hexagon 테이블의 city_id 필드 업데이트)
    await prisma_client.hexagon.update(
        where={
            "session_id_q_r_s": {
                "session_id": game_session_id,
                "q": start_hex.q,
                "r": start_hex.r,
                "s": start_hex.s
            }
        },
        data={
            "city_id": city.id
        }
    )
    
    return city


async def generate_map(game_session_id: str, map_type: MapType, width: int, height: int, seed: int):
    """고도화된 맵 생성 함수 - 실제 DB 데이터 기반"""
    random.seed(seed)
    
    # DB에서 지형 및 자원 정보 사전 로드
    terrains = await prisma_client.terrain.find_many()
    resources = await prisma_client.resource.find_many()
    
    # 지형별 자원 매핑 (지형 특성에 맞는 자원 타입)
    terrain_resource_mapping = {
        'Grassland': ['Wheat', 'Cattle', 'Sheep'],
        'Plains': ['Wheat', 'Horses', 'Cattle'],
        'Forest': ['Deer', 'Dyes', 'Ivory'],
        'Hill': ['Iron', 'Horses', 'Gold'],
        'Tundra': ['Deer'],
        'Desert': ['Salt'],
        'Jungle': ['Spices', 'Dyes', 'Incense'],
        'Coast': ['Fish', 'Whale'],
        'Mountain': ['Silver', 'Gems'],
        'Oasis': ['Gems']
    }
    
    # 맵 타입별 지형 분포 및 특징
    map_type_terrain_distribution = {
        MapType.CONTINENTS: {
            "primary_terrains": ["Grassland", "Plains", "Forest"],
            "secondary_terrains": ["Hill", "Tundra", "Coast"],
            "water_terrains": ["Ocean"],
            "continent_count": 2,
            "continent_size_variance": 0.3
        },
        MapType.PANGAEA: {
            "primary_terrains": ["Plains", "Grassland", "Jungle"],
            "secondary_terrains": ["Hill", "Forest", "Tundra"],
            "water_terrains": ["Ocean", "Coast"],
            "continent_count": 1,
            "continent_size_variance": 0.1
        },
        MapType.ARCHIPELAGO: {
            "primary_terrains": ["Coast"],
            "secondary_terrains": ["Plains", "Hill"],
            "water_terrains": ["Ocean"],
            "continent_count": 10,
            "continent_size_variance": 0.8
        },
        MapType.SMALL_CONTINENTS: {
            "primary_terrains": ["Grassland", "Plains"],
            "secondary_terrains": ["Forest", "Hill", "Coast"],
            "water_terrains": ["Ocean"],
            "continent_count": 4,
            "continent_size_variance": 0.5
        }
    }
    
    # 기본 설정으로 fallback
    current_distribution = map_type_terrain_distribution.get(
        map_type, 
        map_type_terrain_distribution[MapType.CONTINENTS]
    )
    
    # 대륙 생성 알고리즘
    def generate_continent_seed(width, height):
        """대륙의 중심점 생성"""
        return (
            random.randint(width // 4, width * 3 // 4),
            random.randint(height // 4, height * 3 // 4)
        )
    
    # 대륙 중심점들 생성
    continent_seeds = [
        generate_continent_seed(width, height) 
        for _ in range(current_distribution["continent_count"])
    ]
    
    hexagons = []
    
    for q in range(width):
        for r in range(height):
            s = -q - r
            
            # 대륙 중심으로부터의 거리 계산
            distances = [
                math.sqrt((q - seed_q)**2 + (r - seed_r)**2) 
                for seed_q, seed_r in continent_seeds
            ]
            
            # 가장 가까운 대륙 중심 선택
            nearest_continent_index = distances.index(min(distances))
            distance_to_continent = min(distances)
            
            # 대륙 크기와 변동성 고려
            max_continent_radius = min(width, height) * (0.5 + current_distribution["continent_size_variance"])
            normalized_distance = distance_to_continent / max_continent_radius
            
            # 지형 카테고리 결정
            terrain_category = (
                "primary" if normalized_distance < 0.3 else 
                "secondary" if normalized_distance < 0.6 else 
                "water"
            )
            
            # 해당 카테고리의 지형 후보 선택
            terrain_candidates = {
                "primary": current_distribution.get("primary_terrains", []),
                "secondary": current_distribution.get("secondary_terrains", []),
                "water": current_distribution.get("water_terrains", [])
            }.get(terrain_category, [])
            
            # 지형 선택
            terrain_id = random.choice(terrain_candidates) if terrain_candidates else "Plains"
            
            # 자원 선택 로직
            possible_resources = terrain_resource_mapping.get(terrain_id, [])
            
            # 자원 타입 선택 (보너스 > 사치 > 전략)
            resource_type_priorities = ['Bonus', 'Luxury', 'Strategic']
            suitable_resources = [
                r.id for r in resources 
                if r.id in possible_resources and 
                   r.type in resource_type_priorities
            ]
            
            # 랜덤 자원 선택 (일정 확률로 자원 없음)
            resource_id = random.choices(
                [None] + suitable_resources, 
                weights=[0.7] + [0.3 / len(suitable_resources)] * len(suitable_resources)
            )[0]
            
            # 헥사곤 생성
            hexagon = await prisma_client.hexagon.create(
                data={
                    "session_id": game_session_id,
                    "q": q,
                    "r": r,
                    "s": s,
                    "terrain_id": terrain_id,
                    "resource_id": resource_id
                }
            )
            
            hexagons.append(hexagon)
    
    return hexagons

async def ensure_basic_game_data():
    """게임에 필요한 기본 데이터(유닛 타입, 지형, 자원 등)가 존재하는지 확인하고 없으면 생성"""
    # 기본 유닛 타입 정의
    default_unit_types = [
        {
            "id": "settler",
            "name": "정착민",
            "category": "civilian",
            "move": 2,
            "combat_strength": 0,
            "range": 0
        },
        {
            "id": "warrior",
            "name": "전사",
            "category": "melee",
            "move": 2,
            "combat_strength": 10,
            "range": 0
        },
        {
            "id": "scout",
            "name": "정찰병",
            "category": "recon",
            "move": 3,
            "combat_strength": 5,
            "range": 0
        },
        {
            "id": "builder",
            "name": "개척자",
            "category": "civilian",
            "move": 2,
            "combat_strength": 0,
            "range": 0
        },
        {
            "id": "knight",
            "name": "기사",
            "category": "melee",
            "move": 3,
            "combat_strength": 20,
            "range": 0
        },
        {
            "id": "crossbowman",
            "name": "석궁병",
            "category": "ranged",
            "move": 2,
            "combat_strength": 15,
            "range": 2
        }
    ]
    
    # 각 유닛 타입 확인 및 생성
    for unit_type in default_unit_types:
        existing = await prisma_client.unittype.find_unique(
            where={"id": unit_type["id"]}
        )
        
        if not existing:
            await prisma_client.unittype.create(data=unit_type)
    
    # 기본 지형 정의
    default_terrains = [
        {
            "id": "plains",
            "name": "평원",
            "yield_json": json.dumps({"food": 1, "production": 1})
        },
        {
            "id": "grassland",
            "name": "초원",
            "yield_json": json.dumps({"food": 2, "production": 0})
        },
        {
            "id": "desert",
            "name": "사막",
            "yield_json": json.dumps({"food": 0, "production": 0})
        },
        {
            "id": "hills",
            "name": "언덕",
            "yield_json": json.dumps({"food": 0, "production": 2})
        },
        {
            "id": "mountain",
            "name": "산",
            "yield_json": json.dumps({"food": 0, "production": 0})
        },
        {
            "id": "forest",
            "name": "숲",
            "yield_json": json.dumps({"food": 1, "production": 1})
        },
        {
            "id": "tundra",
            "name": "툰드라",
            "yield_json": json.dumps({"food": 1, "production": 0})
        },
        {
            "id": "ocean",
            "name": "대양",
            "yield_json": json.dumps({"food": 1, "production": 0})
        },
        {
            "id": "coast",
            "name": "해안",
            "yield_json": json.dumps({"food": 1, "production": 0})
        },
        {
            "id": "lake",
            "name": "호수",
            "yield_json": json.dumps({"food": 2, "production": 0})
        },
        {
            "id": "jungle",
            "name": "정글",
            "yield_json": json.dumps({"food": 2, "production": 0})
        }
    ]
    
    # 각 지형 확인 및 생성
    for terrain in default_terrains:
        existing = await prisma_client.terrain.find_unique(
            where={"id": terrain["id"]}
        )
        
        if not existing:
            await prisma_client.terrain.create(data=terrain)
    
    # 기본 자원 정의
    default_resources = [
        {
            "id": "wheat",
            "name": "밀",
            "type": "food"
        },
        {
            "id": "cattle",
            "name": "소",
            "type": "food"
        },
        {
            "id": "sheep",
            "name": "양",
            "type": "food"
        },
        {
            "id": "rice",
            "name": "쌀",
            "type": "food"
        },
        {
            "id": "deer",
            "name": "사슴",
            "type": "food"
        },
        {
            "id": "horses",
            "name": "말",
            "type": "strategic"
        },
        {
            "id": "iron",
            "name": "철",
            "type": "production"
        },
        {
            "id": "stone",
            "name": "돌",
            "type": "production"
        },
        {
            "id": "copper",
            "name": "구리",
            "type": "production"
        },
        {
            "id": "gold",
            "name": "금",
            "type": "gold"
        },
        {
            "id": "silver",
            "name": "은",
            "type": "gold"
        },
        {
            "id": "gems",
            "name": "보석",
            "type": "gold"
        },
        {
            "id": "fish",
            "name": "물고기",
            "type": "food"
        },
        {
            "id": "coal",
            "name": "석탄",
            "type": "strategic"
        },
        {
            "id": "oil",
            "name": "석유",
            "type": "strategic"
        }
    ]
    
    # 각 자원 확인 및 생성
    for resource in default_resources:
        existing = await prisma_client.resource.find_unique(
            where={"id": resource["id"]}
        )
        
        if not existing:
            await prisma_client.resource.create(data=resource)
    
    # 기본 개선 시설 정의
    default_improvements = [
        {
            "id": "farm",
            "name": "농장",
            "yield_json": json.dumps({"food": 1})
        },
        {
            "id": "mine",
            "name": "광산",
            "yield_json": json.dumps({"production": 1})
        },
        {
            "id": "pasture",
            "name": "목장",
            "yield_json": json.dumps({"food": 1, "production": 1})
        },
        {
            "id": "camp",
            "name": "캠프",
            "yield_json": json.dumps({"food": 1, "gold": 1})
        },
        {
            "id": "plantation",
            "name": "농원",
            "yield_json": json.dumps({"food": 1, "gold": 1})
        }
    ]
    
    # 각 개선 시설 확인 및 생성
    improvement_table_exists = await prisma_client.raw_query("SELECT to_regclass('public.improvement');")
    if improvement_table_exists and improvement_table_exists[0][0]:
        for improvement in default_improvements:
            existing = await prisma_client.raw_query(f"SELECT id FROM improvement WHERE id = '{improvement['id']}';")
            if not existing or len(existing) == 0:
                await prisma_client.raw_query(
                    f"INSERT INTO improvement (id, name, yield_json) VALUES ('{improvement['id']}', '{improvement['name']}', '{improvement['yield_json']}');"
                )

async def create_initial_units(game_session_id: str, player_id: int, start_hex: Hexagon):
    """플레이어 초기 유닛 생성"""
    # 기본 유닛 타입은 ensure_basic_game_data에서 이미 생성됨
    
    # 정착민 유닛 생성
    settler = await prisma_client.unit.create(
        data={
            "session_id": game_session_id,
            "owner_player_id": player_id,
            "unit_type_id": "settler",
            "hp": 100,
            "movement": 2,
            "max_movement": 2,
            "status": "대기",
            "loc_q": start_hex.q,
            "loc_r": start_hex.r,
            "loc_s": start_hex.s
        }
    )
    
    # 초기 군사 유닛 생성
    warrior = await prisma_client.unit.create(
        data={
            "session_id": game_session_id,
            "owner_player_id": player_id,
            "unit_type_id": "warrior",
            "hp": 100,
            "movement": 2,
            "max_movement": 2,
            "status": "대기",
            "loc_q": start_hex.q,
            "loc_r": start_hex.r,
            "loc_s": start_hex.s
        }
    )
    
    return [settler, warrior]

async def create_initial_city(game_session_id: str, player_id: int, start_hex: Hexagon, civ: str):
    """플레이어 초기 도시 생성"""
    # 문명별 초기 도시 이름 결정
    civ_city_names = {
        "korea": "서울",
        "japan": "도쿄",
        "china": "베이징",
        "mongol": "카라코룸",
        "india": "델리",
        "england": "런던",
        "france": "파리",
        "germany": "베를린",
        "rome": "로마",
        "america": "워싱턴"
    }
    
    city_name = civ_city_names.get(civ, "수도")
    
    city = await prisma_client.city.create(
        data={
            "session_id": game_session_id,
            "name": city_name,
            "owner_player_id": player_id,
            "population": 1,
            "loc_q": start_hex.q,
            "loc_r": start_hex.r,
            "loc_s": start_hex.s,
            "hp": 100,
            "defense": 10,
            "food": 5,
            "production": 3,
            "gold": 10,
            "science": 2,
            "culture": 1,
            "faith": 1,
            "happiness": 10,
            "food_to_next_pop": 10,
            "culture_to_next_border": 20
        }
    )
    
    return city

def hex_distance(a: HexCoord, b: HexCoord) -> int:
    """두 헥스 좌표 사이의 거리 계산"""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))

async def find_starting_position(
    game_session_id: str, 
    occupied_positions: Set[HexCoord],
    min_distance: int = 5
) -> Hexagon:
    """적합한 시작 위치 찾기 (이미 점유된 위치와 일정 거리 이상 떨어진 위치)"""
    # 시작 위치로 적합한 지형
    suitable_terrains = ["grassland", "plains"]
    
    # 모든 적합한 타일 조회
    suitable_hexes = await prisma_client.hexagon.find_many(
        where={
            "session_id": game_session_id,
            "terrain_id": {"in": suitable_terrains}
        }
    )
    
    if not suitable_hexes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="적합한 시작 위치를 찾을 수 없습니다."
        )
    
    # 적합한 위치 중 이미 점유된 위치와 일정 거리 이상 떨어진 위치 찾기
    for hex in suitable_hexes:
        hex_coord = (hex.q, hex.r, hex.s)
        
        # 이미 점유된 위치와의 거리 확인
        is_valid = True
        for occupied in occupied_positions:
            if hex_distance(hex_coord, occupied) < min_distance:
                is_valid = False
                break
        
        if is_valid:
            # 근처에 좋은 자원이 있는지 확인 (보너스)
            nearby_resources = await prisma_client.hexagon.find_many(
                where={
                    "session_id": game_session_id,
                    "q": {"gte": hex.q - 2, "lte": hex.q + 2},
                    "r": {"gte": hex.r - 2, "lte": hex.r + 2},
                    "resource_id": {"not": None}
                }
            )
            
            # 자원이 있으면 가중치 더 높게
            if nearby_resources and len(nearby_resources) >= 2:
                return hex
    
    # 자원 주변 위치를 찾지 못했다면, 기본 조건만 만족하는 위치 반환
    for hex in suitable_hexes:
        hex_coord = (hex.q, hex.r, hex.s)
        
        is_valid = True
        for occupied in occupied_positions:
            if hex_distance(hex_coord, occupied) < min_distance:
                is_valid = False
                break
        
        if is_valid:
            return hex
    
    # 최소 거리 조건을 만족하는 위치가 없다면, 그냥 아무 적합한 위치 반환
    return random.choice(suitable_hexes)

@router.post("/start", response_model=GameSessionResponse)
async def create_game_session(request: GameSessionCreate):
    """게임 세션 생성"""
    try:
        # 0. 기본 유닛 타입, 지형, 자원 등 기본 데이터 확인 및 생성
        await ensure_basic_game_data()
        
        # 1. 유효성 검사
        if not (5 <= request.civCount <= 10):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="문명 수는 5-10 사이여야 합니다."
            )
        
        # 2. 게임 세션 생성
        current_time = datetime.now()
        game_session = await prisma_client.gamesession.create(
            data={
                "host_user_id": 1,
                "map_type_id": request.mapType.value,
                "game_mode_id": request.gameSpeed,
                "difficulty_id": request.difficulty.value,
                "civ_count": request.civCount,
                "seed": int(time.time() * 1000),
                "current_turn": 1,
                "current_player": 1,
                "status": "ongoing",
                "created_at": current_time,
                "updated_at": current_time
            }
        )
        
        # 3. 맵 생성
        hexagons = await generate_map(
            game_session.id, 
            request.mapType, 
            settings.DEFAULT_MAP_WIDTH, 
            settings.DEFAULT_MAP_HEIGHT, 
            game_session.seed
        )
        
        # 이미 점유된 시작 위치 추적
        occupied_positions: Set[HexCoord] = set()
        
        # 4. 플레이어 생성
        player = await prisma_client.player.create(
            data={
                "session_id": game_session.id,
                "user_id": 1,  # TODO: 실제 사용자 ID
                "civ_type": request.playerCiv,
                "is_ai": False,
                "player_index": 0
            }
        )
        
        # 5. 플레이어 시작 위치를 왼쪽 상단으로 고정
        # 맵의 왼쪽 상단 영역에서 적합한 시작 타일 찾기
        map_width = settings.DEFAULT_MAP_WIDTH
        map_height = settings.DEFAULT_MAP_HEIGHT
        
        # 왼쪽 상단 영역 정의 (맵의 1/4 영역)
        left_upper_hexes = await prisma_client.hexagon.find_many(
            where={
                "session_id": game_session.id,
                "q": {"lte": map_width // 3},
                "r": {"lte": map_height // 3},
                "terrain_id": {"in": ["grassland", "plains"]}
            }
        )
        
        if not left_upper_hexes:
            # 왼쪽 상단에 적합한 타일이 없으면 일반적인 방법으로 시작 위치 찾기
            start_hex = await find_starting_position(game_session.id, occupied_positions)
        else:
            # 왼쪽 상단 영역에서 가장 적합한 타일 선택 (자원이 인접해 있는 타일 우선)
            best_hex = None
            best_resource_count = -1
            
            for hex in left_upper_hexes:
                # 주변 자원 확인
                nearby_resources = await prisma_client.hexagon.find_many(
                    where={
                        "session_id": game_session.id,
                        "q": {"gte": hex.q - 2, "lte": hex.q + 2},
                        "r": {"gte": hex.r - 2, "lte": hex.r + 2},
                        "resource_id": {"not": None}
                    }
                )
                
                if len(nearby_resources) > best_resource_count:
                    best_resource_count = len(nearby_resources)
                    best_hex = hex
            
            # 자원이 없는 경우에도 왼쪽 상단의 타일 하나 선택
            start_hex = best_hex if best_hex else random.choice(left_upper_hexes)
        
        # 시작 위치 점유 표시
        player_capital_coord = (start_hex.q, start_hex.r, start_hex.s)
        occupied_positions.add(player_capital_coord)
        
        # 수도 타일 기본 수확량 설정
        await setup_capital_yield(game_session.id, [player_capital_coord])
        
        # 6. 초기 도시 생성 (수도)
        initial_city = await create_initial_city(game_session.id, player.id, start_hex, request.playerCiv)
        
        # 7. AI 문명 생성 및 배치
        ai_civs = [
            "china", "rome", "egypt", "japan", "france", 
            "germany", "england", "america", "india", "russia"
        ]
        if request.playerCiv in ai_civs:
            ai_civs.remove(request.playerCiv)
        
        # AI 문명 수가 충분한지 확인
        if len(ai_civs) < request.civCount - 1:
            ai_civs.extend(["aztec", "babylon", "persia", "greece", "spain"])
        
        # AI 무작위 섞기
        random.shuffle(ai_civs)
        
        # AI 시작 위치 간의 최소 거리 증가 (5칸 -> 7칸)
        min_distance_between_ai = 5
        min_distance_from_player = 7  # 플레이어로부터 최소 7칸 떨어지도록 설정
        
        ai_capital_coords = []  # AI 수도 좌표 리스트
        ai_players_data = []    # AI 플레이어 정보 리스트
        
        for i in range(1, request.civCount):
            ai_civ = ai_civs[i-1]
            
            ai_player = await prisma_client.player.create(
                data={
                    "session_id": game_session.id,
                    "user_id": 1,  # 시스템 사용자
                    "civ_type": ai_civ,
                    "is_ai": True,
                    "player_index": i
                }
            )
            
            ai_players_data.append(ai_player)
            
            # 플레이어 위치에서 충분히 떨어진 위치 찾기
            player_pos = player_capital_coord
            
            # 모든 적합한 타일 조회
            suitable_hexes = await prisma_client.hexagon.find_many(
                where={
                    "session_id": game_session.id,
                    "terrain_id": {"in": ["grassland", "plains"]}
                }
            )
            
            # 플레이어와 다른 AI로부터 충분히 떨어진 위치 찾기
            valid_hexes = []
            for hex in suitable_hexes:
                hex_coord = (hex.q, hex.r, hex.s)
                
                # 플레이어로부터의 거리 확인
                dist_to_player = hex_distance(hex_coord, player_pos)
                if dist_to_player < min_distance_from_player:
                    continue
                
                # 다른 AI로부터의 거리 확인
                too_close = False
                for occupied in occupied_positions:
                    if hex_distance(hex_coord, occupied) < min_distance_between_ai:
                        too_close = True
                        break
                
                if not too_close:
                    valid_hexes.append(hex)
            
            # 유효한 위치가 없으면 거리 제약 완화
            if not valid_hexes:
                for hex in suitable_hexes:
                    hex_coord = (hex.q, hex.r, hex.s)
                    
                    # 플레이어로부터의 거리만 확인 (최소 5칸)
                    dist_to_player = hex_distance(hex_coord, player_pos)
                    if dist_to_player >= 5:
                        valid_hexes.append(hex)
            
            # 그래도 위치가 없으면 일반적인 방법으로 찾기
            if valid_hexes:
                ai_start_hex = random.choice(valid_hexes)
            else:
                ai_start_hex = await find_starting_position(game_session.id, occupied_positions, min_distance=5)
            
            if ai_start_hex:
                # 시작 위치 점유 표시
                ai_capital_coord = (ai_start_hex.q, ai_start_hex.r, ai_start_hex.s)
                occupied_positions.add(ai_capital_coord)
                ai_capital_coords.append(ai_capital_coord)
                
                # 수도 타일 기본 수확량 설정
                await setup_capital_yield(game_session.id, [ai_capital_coord])
                
                # AI 초기 도시 생성
                await create_initial_city(game_session.id, ai_player.id, ai_start_hex, ai_civ)
        
        # 모든 플레이어 수도 좌표 리스트
        all_capital_coords = [player_capital_coord] + ai_capital_coords
        
        # 8. 각 수도 반경 2칸 내에 보장 자원 배치
        await assign_guaranteed_resources(game_session.id, all_capital_coords)
        
        # 9. 전체 맵에 자원 분포
        await distribute_map_resources(game_session.id)
        
        # 10. 플레이어 초기 유닛 생성 - Scout와 Builder
        initial_units = await create_starting_units(game_session.id, player.id, start_hex)
        
        # 11. AI 초기 유닛 생성
        for i, ai_player in enumerate(ai_players_data):
            if i < len(ai_capital_coords):
                ai_capital_hex = await prisma_client.hexagon.find_unique(
                    where={
                        "session_id_q_r_s": {
                            "session_id": game_session.id,
                            "q": ai_capital_coords[i][0],
                            "r": ai_capital_coords[i][1],
                            "s": ai_capital_coords[i][2]
                        }
                    }
                )
                
                if ai_capital_hex:
                    await create_starting_units(game_session.id, ai_player.id, ai_capital_hex)
        
        # 12. 초기 개선 추천 목록 생성
        suggested_improvements = await get_suggested_improvements(game_session.id, player_capital_coord)
        
        # 13. 초기 게임 상태 정의
        initial_state = {
            "gameId": game_session.id,
            "turn": 1,
            "year": -4000,
            "playerId": str(player.id),
            "playerCiv": request.playerCiv,
            "resources": {
                "food": 10,
                "production": 5,
                "gold": 20,
                "science": 3,
                "culture": 2,
                "faith": 1,
                "happiness": 10
            },
            "cities": [{
                "id": initial_city.id,
                "name": initial_city.name,
                "population": initial_city.population,
                "production": initial_city.production,
                "turnsLeft": 3,
                "food": initial_city.food,
                "gold": initial_city.gold,
                "science": initial_city.science,
                "culture": initial_city.culture,
                "faith": initial_city.faith,
                "happiness": initial_city.happiness,
                "hp": initial_city.hp,
                "defense": initial_city.defense,
                # 위치 정보 추가
                "location": {
                    "q": initial_city.loc_q,
                    "r": initial_city.loc_r,
                    "s": initial_city.loc_s
                }
            }],
            "units": [{
                "id": unit.id,
                "name": unit.unit_type_id,
                "type": unit.unit_type_id,
                "typeName": unit.unit_type_id,
                "hp": unit.hp,
                "maxHp": unit.hp,
                "movement": unit.movement,
                "maxMovement": unit.max_movement,
                "status": unit.status,
                "location": {
                    "q": unit.loc_q,
                    "r": unit.loc_r,
                    "s": unit.loc_s
                },
                "charges": unit.charges if hasattr(unit, 'charges') else None
            } for unit in initial_units],
            "diplomacy": {
                "civs": [],
                "cityStates": []
            },
            "naturalWonders": [],
            "researchState": {
                "science": 3,
                "progress": 0,
                "currentTechId": None,
                "researchedTechIds": []
            },
            "policyState": {
                "culture": 2,
                "adopted": [],
                "ideology": None
            },
            "religionState": {
                "faith": 1,
                "foundedReligionId": None,
                "followerReligionId": None
            },
            "suggestedImprovements": suggested_improvements
        }
        
        # 프론트엔드가 기대하는 응답 형식으로 변경
        game_session_response = GameSessionResponse(
            id=game_session.id,
            playerName=request.playerName,
            mapType=game_session.map_type_id,
            difficulty=request.difficulty,
            currentTurn=game_session.current_turn,
            gameSpeed=request.gameSpeed,
            createdAt=game_session.created_at,
            updatedAt=game_session.updated_at,
            initialState=initial_state  # 초기 게임 상태 추가
        )
        
        return game_session_response
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"게임 세션 생성 중 오류 발생: {str(e)}"
        )


@router.get("/options", response_model=Dict[str, List[Dict[str, str]]])
async def get_game_options():
    """게임 옵션 목록 반환"""
    try:
        # 맵 타입 조회
        map_types = await prisma_client.maptype.find_many()
        
        # 난이도 조회
        difficulties = await prisma_client.difficulty.find_many()
        
        # 문명 조회
        civilizations = await prisma_client.civilization.find_many()
        
        # 게임 모드 조회 
        game_modes = await prisma_client.gamemode.find_many()
        
        # 응답 데이터 구성
        map_types_response = [
            {
                "id": map_type.id,
                "name": map_type.name,
                "description": map_type.description or get_map_type_description(MapType(map_type.id))
            } for map_type in map_types
        ]
        
        difficulties_response = [
            {
                "id": difficulty.id,
                "name": difficulty.name,
                "description": difficulty.description or get_difficulty_description(Difficulty(difficulty.id))
            } for difficulty in difficulties
        ]
        
        civilizations_response = [
            {
                "id": civ.id,
                "name": civ.name,
                "leader": civ.leader,
                "specialAbility": civ.specialAbility
            } for civ in civilizations
        ]
        
        game_modes_response = [
        {
            "id": mode.id,
                "name": mode.name,
                "turns": str(mode.turns),  # 정수를 문자열로 변환
                "estimatedTime": mode.estimatedTime,
                "description": mode.description
            } for mode in game_modes
        ]
        
        return {
            "mapTypes": map_types_response,
            "difficulties": difficulties_response,
            "civilizations": civilizations_response,
            "gameModes": game_modes_response
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"게임 옵션 조회 중 오류 발생: {str(e)}"
        )

# 유닛 이동 처리 함수
async def move_unit(game_id: str, unit_id: str, to_q: int, to_r: int, to_s: int):
    """유닛을 새로운 위치로 이동시키는 함수"""
    
    # 게임 세션 확인
    game_session = await prisma_client.gamesession.find_unique(
        where={"id": game_id},
        include={"players": True}
    )
    
    if not game_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="존재하지 않는 게임입니다."
        )
    
    # 유닛 정보 조회
    unit = await prisma_client.unit.find_unique(
        where={"id": unit_id},
        include={"owner": True}
    )
    
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="유닛을 찾을 수 없습니다."
        )
    
    # 게임 세션과 유닛의 연결 확인
    if unit.session_id != game_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이 게임에 속한 유닛이 아닙니다."
        )
    
    # 목적지 타일 확인
    target_hex = await prisma_client.hexagon.find_unique(
        where={
            "session_id_q_r_s": {
                "session_id": game_id,
                "q": to_q,
                "r": to_r,
                "s": to_s
            }
        }
    )
    
    if not target_hex:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="이동할 타일이.존재하지 않습니다."
        )
    
    # 이동 불가능한 타일 체크 (산, 바다 등)
    impassable_terrains = ["Ocean", "Mountain"]
    if target_hex.terrain_id in impassable_terrains:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이동할 수 없는 지형입니다."
        )
    
    # 현재 위치와 목적지 간의 거리 계산
    current_pos = (unit.loc_q, unit.loc_r, unit.loc_s)
    target_pos = (to_q, to_r, to_s)
    
    # hex_distance 함수 호출 (이미 정의되어 있음)
    distance = hex_distance(current_pos, target_pos)
    
    # 이동 가능 거리 확인
    if distance > unit.movement:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"이동 가능한 거리를 초과했습니다. (가능: {unit.movement}, 필요: {distance})"
        )
    
    # 목적지에 다른 아군 유닛이 있는지 확인
    other_unit = await prisma_client.unit.find_first(
        where={
            "session_id": game_id,
            "loc_q": to_q,
            "loc_r": to_r,
            "loc_s": to_s,
            "NOT": {
                "id": unit_id
            }
        }
    )
    
    if other_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 다른 유닛이 있는 타일입니다."
        )
    
    # 출발지 타일에서 유닛 제거
    from_hex = await prisma_client.hexagon.find_unique(
        where={
            "session_id_q_r_s": {
                "session_id": game_id,
                "q": unit.loc_q,
                "r": unit.loc_r,
                "s": unit.loc_s
            }
        }
    )
    
    if from_hex:
        await prisma_client.hexagon.update(
            where={
                "session_id_q_r_s": {
                    "session_id": game_id,
                    "q": unit.loc_q,
                    "r": unit.loc_r,
                    "s": unit.loc_s
                }
            },
            data={
                "unit_id": None
            }
        )
    
    # 유닛의 위치 업데이트
    updated_unit = await prisma_client.unit.update(
        where={"id": unit_id},
        data={
            "loc_q": to_q,
            "loc_r": to_r,
            "loc_s": to_s,
            "movement": unit.movement - distance,
            "status": "이동 중" if unit.movement - distance > 0 else "대기"
        }
    )
    
    # 도착지 타일에 유닛 배치
    await prisma_client.hexagon.update(
        where={
            "session_id_q_r_s": {
                "session_id": game_id,
                "q": to_q,
                "r": to_r,
                "s": to_s
            }
        },
        data={
            "unit_id": unit_id
        }
    )
    
    # 시야 업데이트 - 유닛이 이동한 새 위치 주변 타일을 탐험됨/보임으로 설정
    # 유닛 주변 1칸까지 모두 보이도록 설정
    # 모든 인접 타일 가져오기
    neighboring_hexes = await prisma_client.hexagon.find_many(
        where={
            "session_id": game_id,
            "OR": [
                {"AND": [
                    {"q": to_q + dq},
                    {"r": to_r + dr},
                    {"s": to_s + ds}
                ]} for dq, dr, ds in [
                    (1, 0, -1), (1, -1, 0), (0, -1, 1), 
                    (-1, 0, 1), (-1, 1, 0), (0, 1, -1)
                ]
            ]
        }
    )
    
    # 시야 업데이트
    for hex in neighboring_hexes:
        await prisma_client.hexagon.update(
            where={
                "session_id_q_r_s": {
                    "session_id": game_id,
                    "q": hex.q,
                    "r": hex.r,
                    "s": hex.s
                }
            },
            data={
                "visible": True,
                "explored": True
            }
        )
    
    # 목적지 타일 자체도 보이도록 설정
    await prisma_client.hexagon.update(
        where={
            "session_id_q_r_s": {
                "session_id": game_id,
                "q": to_q,
                "r": to_r,
                "s": to_s
            }
        },
        data={
            "visible": True,
            "explored": True
        }
    )
    
    # 응답 데이터 구성
    return {
        "id": updated_unit.id,
        "name": updated_unit.unit_type_id,
        "type": updated_unit.unit_type_id,
        "typeName": updated_unit.unit_type_id,
        "hp": updated_unit.hp,
        "movement": updated_unit.movement,
        "maxMovement": updated_unit.max_movement,
        "status": updated_unit.status,
        "location": {
            "q": updated_unit.loc_q,
            "r": updated_unit.loc_r,
            "s": updated_unit.loc_s
        }
    }

# 유닛 이동 API 엔드포인트
@router.post("/unit/move", response_model=UnitResponse)
async def unit_move(request: UnitMoveRequest):
    """유닛 이동 처리 API"""
    return await move_unit(
        request.gameId,
        request.unitId,
        request.to.q,
        request.to.r,
        request.to.s
    )

# 턴 종료 엔드포인트
@router.post("/turn/end-turn", response_model=TurnEndResponse)
async def end_turn(request: TurnEndRequest):
    """턴 종료 처리"""
    try:
        # 턴 종료 처리
        turn_result = await process_turn_end(request.game_id, request.player_id)
        
        # WebSocket 알림 기능 제거, 결과만 반환
        return turn_result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"턴 종료 처리 중 오류 발생: {str(e)}"
        )

# 게임 현재 상태 조회 엔드포인트
@router.get("/state/{game_id}")
async def get_game_state(game_id: str):
    """게임 현재 상태 조회"""
    try:
        # 게임 세션 정보 조회
        game_session = await prisma_client.gamesession.find_unique(
            where={"id": game_id},
            include={"players": True}
        )
        
        if not game_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 게임입니다."
            )
        
        # 게임 시나리오 정보 (목표, 키워드 등)
        from utils.scenario_manager import get_or_create_scenario, get_turn_info
        
        scenario = await get_or_create_scenario(game_id)
        speed = GameSpeed(game_session.game_mode_id)
        current_turn = game_session.current_turn
        
        # 현재 턴 정보 생성
        current_phase, objectives, recommended_actions = get_turn_info(scenario, current_turn)
        turn_year = calculate_turn_year(current_turn, speed)
        
        # 플레이어 정보 조회
        player_data = []
        for player in game_session.players:
            cities = await prisma_client.city.find_many(
                where={
                    "session_id": game_id,
                    "owner_player_id": player.id
                }
            )
            
            units = await prisma_client.unit.find_many(
                where={
                    "session_id": game_id,
                    "owner_player_id": player.id
                }
            )
            
            player_data.append({
                "id": player.id,
                "name": player.civ_type,
                "is_ai": player.is_ai,
                "cities": len(cities),
                "units": len(units)
            })
        
        # 턴 정보 구성
        turn_info = GameTurnInfo(
            turn=current_turn,
            phase=current_phase,
            year=turn_year,
            objectives=objectives,
            recommended_actions=recommended_actions
        )
        
        # 응답 데이터 구성
        return {
            "game_id": game_id,
            "current_turn": current_turn,
            "map_type": game_session.map_type_id,
            "game_speed": game_session.game_mode_id,
            "turn_info": turn_info.dict(),
            "players": player_data,
            "status": game_session.status,
            "created_at": game_session.created_at,
            "updated_at": game_session.updated_at
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"게임 상태 조회 중 오류 발생: {str(e)}"
        )

# 목표 완료 엔드포인트
@router.post("/objective/complete")
async def complete_objective(game_id: str, objective_id: str, player_id: str):
    """목표 완료 처리"""
    try:
        # 목표 완료 처리
        from utils.scenario_manager import get_or_create_scenario, check_objective_completion
        
        scenario = await get_or_create_scenario(game_id)
        completed = check_objective_completion(scenario, objective_id)
        
        if completed:
            # 보상 지급 로직 (실제 구현 필요)
            
            # 웹소켓으로 목표 완료 알림
            message = {
                "type": "objective_completed",
                "player_id": player_id,
                "timestamp": datetime.now().isoformat(),
                "content": {
                    "objective_id": objective_id,
                    "description": "목표를 달성했습니다!"
                }
            }
            
            await ws_manager.broadcast(game_id, message)
            
            return {"status": "success", "message": "목표가 완료되었습니다."}
        else:
            return {"status": "error", "message": "해당 목표를 찾을 수 없거나 이미 완료되었습니다."}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"목표 완료 처리 중 오류 발생: {str(e)}"
        )
