from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Dict, Any, Optional
from models.hexmap import HexTile, TerrainType, ResourceType, GameMapState, HexCoord, Civilization
import random
import math
import uuid
from datetime import datetime
from prisma import Prisma
import json

# Prisma 클라이언트 인스턴스
prisma = Prisma()

router = APIRouter()

@router.get("/data", summary="맵 데이터 조회", response_description="맵 데이터 반환")
async def get_map_data(user_id: Optional[str] = Query(None, description="사용자 ID")):
    """내륙 바다(Inland Sea) 형태의 맵 데이터 반환"""
    try:
        # 임시 유저 ID 생성 (user_id가 제공되지 않은 경우)
        if not user_id:
            user_id = f"temp_user_{uuid.uuid4().hex[:8]}"
            
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
        
        # 사용자 ID를 정수로 변환 (없는 경우 기본값 1 사용)
        user_id_int = int(user_id) if user_id and user_id.isdigit() else 1

        # 사용자 존재 확인
        user = await prisma.user.find_unique(
            where={"id": user_id_int}
        )

        # 사용자가 없으면 생성
        if not user:
            # 기본 사용자 생성 (임시)
            user = await prisma.user.create(
                data={
                    "id": user_id_int,
                    "username": f"user_{user_id_int}",
                    "password_hash": "temporary_hash",
                    "created_at": datetime.now()
                }
            )
        
        # 사용자의 기존 게임 조회
        # 버전 호환성 문제로 order_by 대신 정렬 없이 조회 후 프로그램에서 정렬
        games = await prisma.game.find_many(
            where={"userId": user_id},  # DB 스키마에서 userId는 String 타입입니다
            include={"gameStates": True}
        )
        
        # 게임이 존재하면 가장 최근 게임을 선택 (updatedAt 기준 정렬)
        existing_game = None
        if games:
            # 수동으로 정렬하여 가장 최근 게임 찾기
            existing_game = sorted(games, key=lambda g: g.updatedAt, reverse=True)[0]
        
        # 기존 게임이 있는 경우
        if existing_game and existing_game.gameStates and len(existing_game.gameStates) > 0:
            # 가장 최신 턴의 게임 상태 조회
            latest_game_state = await prisma.gamestate.find_first(
                where={"gameId": existing_game.id, "turn": existing_game.currentTurn}
            )
            
            if latest_game_state:
                # 게임 상태 데이터 가져오기
                game_map_state_data = latest_game_state.stateData
                
                # 플레이어 정보 조회
                player = await prisma.player.find_first(
                    where={
                        "session_id": existing_game.id,
                        "is_ai": False
                    }
                )
                
                # 플레이어가 없는 경우 (비정상 데이터)
                if not player:
                    # 임시 플레이어 객체 생성 (id만 필요)
                    player = type('Player', (), {'id': f'temp_{uuid.uuid4().hex}'})
                
                # 플레이어 도시 위치 찾기
                player_city = None
                if "civs" in game_map_state_data and len(game_map_state_data["civs"]) > 0:
                    korea_civ = next((civ for civ in game_map_state_data["civs"] if civ["name"] == "Korea"), None)
                    if korea_civ and "capital_tile" in korea_civ:
                        player_city = {
                            "name": "Seoul",
                            "q": korea_civ["capital_tile"]["q"],
                            "r": korea_civ["capital_tile"]["r"],
                            "s": -korea_civ["capital_tile"]["q"] - korea_civ["capital_tile"]["r"],
                            "city_id": f"city_{korea_civ['name'].lower()}"
                        }
                
                # 성공 응답 반환 (기존 게임 데이터)
                return {
                    "success": True,
                    "status_code": 200,
                    "message": "기존 맵 데이터가 성공적으로 로드되었습니다.",
                    "data": game_map_state_data,
                    "player_city": player_city,
                    "game_id": existing_game.id,
                    "turn": existing_game.currentTurn,
                    "is_new_game": False,
                    "playerId": str(player.id),
                    "meta": {
                        "width": existing_game.width,
                        "height": existing_game.height,
                        "tile_count": len(game_map_state_data["tiles"]) if "tiles" in game_map_state_data else 0,
                        "civ_count": len(game_map_state_data["civs"]) if "civs" in game_map_state_data else 0
                    }
                }
        
        # 기존 게임이 없거나 게임 상태가 없는 경우 새 게임 생성
        # 맵 크기 설정
        width = 21
        height = 19
        
        # 내륙 바다 맵 생성
        hexagons = generate_inland_sea_map(width, height)
        
        # 문명 정보 - 한국(플레이어) + 5개 AI 문명
        civilizations = [
            Civilization(
                name="Korea",
                capital_tile=HexCoord(q=4, r=3),
                units=["warrior-1", "settler-1"]
            ),
            Civilization(
                name="Japan",
                capital_tile=HexCoord(q=16, r=3),
                units=["warrior-2"]
            ),
            Civilization(
                name="China",
                capital_tile=HexCoord(q=4, r=15),
                units=["warrior-3"]
            ),
            Civilization(
                name="Mongolia",
                capital_tile=HexCoord(q=16, r=15),
                units=["warrior-4"]
            ),
            Civilization(
                name="Russia",
                capital_tile=HexCoord(q=10, r=2),
                units=["warrior-5"]
            ),
            Civilization(
                name="Rome",
                capital_tile=HexCoord(q=10, r=16),
                units=["warrior-6"]
            ),
        ]
        
        # 게임 맵 상태 생성 (1턴으로 시작)
        game_map_state = GameMapState(
            tiles=hexagons,
            civs=civilizations,
            turn=1,
            game_id="inland_sea_map"
        )
        
        # 유저(한국) 도시 위치 정보
        player_city = {
            "name": "Seoul",  # 수도 이름
            "q": 4,  # q 좌표
            "r": 3,  # r 좌표
            "s": -7,  # s 좌표 (q + r + s = 0)
            "city_id": "city_korea"
        }
        
        # 게임 ID 생성 (명시적으로 생성)
        game_id = str(uuid.uuid4())
        
        # Prisma를 사용해 DB에 게임 상태 저장
        try:
            
            # 게임 맵 상태를 JSON으로 직렬화
            state_data_json = json.dumps(game_map_state.dict())
            
            # 게임 생성
            new_game = await prisma.game.create(
                data={
                    "id": game_id,
                    "userId": user_id,  # String 타입으로 유지
                    "currentTurn": 1,
                    "mapType": "inland_sea",
                    "width": width,
                    "height": height
                }
            )
            
            # 현재 날짜와 시간 가져오기
            current_time = datetime.now()

            # GameSession 생성 전에 필요한 기본 데이터 확인 및 생성
            # 맵 타입 확인
            map_type = await prisma.maptype.find_unique(
                where={"id": "inland_sea"}
            )
            if not map_type:
                # 맵 타입이 없으면 생성
                map_type = await prisma.maptype.create(
                    data={
                        "id": "inland_sea",
                        "name": "Inland Sea",
                        "description": "내륙 바다 맵 타입",
                        "features": "바다가 중앙에 위치"
                    }
                )

            # 게임 모드 확인
            game_mode = await prisma.gamemode.find_unique(
                where={"id": "standard"}
            )
            if not game_mode:
                # 게임 모드가 없으면 생성
                game_mode = await prisma.gamemode.create(
                    data={
                        "id": "standard",
                        "name": "Standard",
                        "turns": 500,
                        "estimatedTime": "8-12 hours",
                        "description": "표준 게임 모드"
                    }
                )

            # 난이도 확인
            difficulty = await prisma.difficulty.find_unique(
                where={"id": "normal"}
            )
            if not difficulty:
                # 난이도가 없으면 생성
                difficulty = await prisma.difficulty.create(
                    data={
                        "id": "normal",
                        "name": "Normal",
                        "description": "보통 난이도",
                        "aiBonus": "없음",
                        "playerPenalty": "없음"
                    }
                )

            # 문명 데이터 확인 및 생성
            for civ_id in ["Korea", "Japan", "China", "Mongolia", "Russia", "Rome"]:
                civ = await prisma.civilization.find_unique(
                    where={"id": civ_id}
                )
                if not civ:
                    # 기본 리더 이름 설정
                    leader_name = "Unknown"
                    if civ_id == "Korea":
                        leader_name = "Sejong"
                    elif civ_id == "Japan":
                        leader_name = "Oda Nobunaga"
                    elif civ_id == "China":
                        leader_name = "Wu Zetian"
                    elif civ_id == "Mongolia":
                        leader_name = "Genghis Khan"
                    elif civ_id == "Russia":
                        leader_name = "Catherine"
                    elif civ_id == "Rome":
                        leader_name = "Augustus Caesar"
                        
                    # 문명 생성
                    await prisma.civilization.create(
                        data={
                            "id": civ_id,
                            "name": civ_id,
                            "leader": leader_name,
                            "specialAbility": f"{civ_id} 특수 능력",
                            "specialUnit": f"{civ_id} 특수 유닛",
                            "specialBuilding": f"{civ_id} 특수 건물"
                        }
                    )

            # GameSession 생성 (Player가 참조하는 테이블)
            game_session = await prisma.gamesession.create(
                data={
                    "id": game_id,  # 동일한 ID 사용
                    "host_user_id": user_id_int,
                    "map_type_id": "inland_sea",  # 기본 맵 타입
                    "game_mode_id": "standard",   # 기본 게임 모드
                    "difficulty_id": "normal",    # 기본 난이도
                    "seed": random.randint(1, 999999),
                    "current_turn": 1,
                    "current_player": 0,
                    "created_at": current_time,
                    "updated_at": current_time
                }
            )
            
            # 플레이어 생성 (한국 - 플레이어)
            player = await prisma.player.create(
                data={
                    "session_id": game_id,
                    "user_id": user_id_int,  # 실제 유저 ID 사용 (정수 타입)
                    "civ_id": "Korea",
                    "is_ai": False,
                    "player_index": 0
                }
            )
            
            # AI 플레이어 생성
            ai_civs = ["Japan", "China", "Mongolia", "Russia", "Rome"]
            for i, civ in enumerate(ai_civs):
                await prisma.player.create(
                    data={
                        "session_id": game_id,
                        "user_id": user_id_int,  # 시스템 사용자(실제 사용자의 ID 사용) (정수 타입)
                        "civ_id": civ,
                        "is_ai": True,
                        "player_index": i + 1
                    }
                )
            
            # 게임 상태 별도 생성
            await prisma.gamestate.create(
                data={
                    "gameId": game_id,
                    "turn": 1,
                    "stateData": state_data_json
                }
            )
            
            
            # 성공 응답 반환 (새 게임 데이터)
            success_response = {
                "success": True,
                "status_code": 200,
                "message": "새 맵 데이터가 성공적으로 생성되었습니다.",
                "data": game_map_state,
                "player_city": player_city,
                "game_id": game_id,
                "turn": 1,
                "is_new_game": True,
                "playerId": str(player.id),
                "meta": {
                    "width": width,
                    "height": height,
                    "tile_count": len(hexagons),
                    "civ_count": len(civilizations)
                }
            }
            
        except Exception as db_error:
            # DB 오류 처리
            
            # 게임은 계속 진행 (DB 저장 실패해도 게임은 보여줌)
            # 그러나 나중에 저장된 게임이 없으므로 새 게임으로 시작
            success_response = {
                "success": True,
                "status_code": 200,
                "message": "새 맵 데이터가 성공적으로 생성되었습니다. (DB 저장 실패)",
                "data": game_map_state,
                "player_city": player_city,
                "game_id": game_id,
                "turn": 1,
                "is_new_game": True,
                "playerId": "temp_" + str(uuid.uuid4()),  # 임시 ID 생성
                "meta": {
                    "width": width,
                    "height": height,
                    "tile_count": len(hexagons),
                    "civ_count": len(civilizations)
                }
            }
            
        return success_response
        
    except Exception as e:
        # 오류 로깅 (실제 운영 환경에서는 로깅 시스템 사용)
        
        # 에러 응답 반환
        return {
            "success": False,
            "status_code": 500,
            "message": f"맵 데이터 로드 중 오류가 발생했습니다: {str(e)}",
            "error": {
                "type": type(e).__name__,
                "detail": str(e)
            }
        }


def generate_inland_sea_map(width: int, height: int) -> List[HexTile]:
    """내륙 바다 맵 생성 함수"""
    hexagons = []
    
    # 중심점 계산
    center_q = width // 2
    center_r = height // 2
    
    # 내륙 바다 반경
    sea_radius = min(width, height) // 3
    
    # 문명 시작 위치 정의
    civ_positions = {
        "Korea": {"q": 4, "r": 3, "city_id": "city_korea", "unit_id": "warrior-1", "unit_q": 5, "unit_r": 3},
        "Japan": {"q": 16, "r": 3, "city_id": "city_japan", "unit_id": "warrior-2", "unit_q": 17, "unit_r": 3},
        "China": {"q": 4, "r": 15, "city_id": "city_china", "unit_id": "warrior-3", "unit_q": 5, "unit_r": 15},
        "Mongolia": {"q": 16, "r": 15, "city_id": "city_mongolia", "unit_id": "warrior-4", "unit_q": 17, "unit_r": 15},
        "Russia": {"q": 10, "r": 2, "city_id": "city_russia", "unit_id": "warrior-5", "unit_q": 11, "unit_r": 2},
        "Rome": {"q": 10, "r": 16, "city_id": "city_rome", "unit_id": "warrior-6", "unit_q": 11, "unit_r": 16}
    }
    
    # 각 타일 생성
    for q in range(width):
        for r in range(height):
            s = -q - r  # 큐브 좌표 제약: q + r + s = 0
            
            # 중심점으로부터의 거리 계산
            distance = max(
                abs(q - center_q),
                abs(r - center_r),
                abs(s - (-center_q - center_r))
            )
            
            # 내륙 바다 영역 판단 (중심에 바다)
            is_sea = distance < sea_radius
            
            # 맵 가장자리 설정 (대양)
            is_edge = q == 0 or r == 0 or q == width - 1 or r == height - 1
            
            # 지형 결정 (내륙 바다, 해안, 육지)
            if is_edge:
                # 가장자리는 산
                terrain = TerrainType.MOUNTAIN
                resource = None
                explored = False
                visible = False
            elif is_sea:
                # 중앙 내륙 바다
                terrain = TerrainType.OCEAN if distance < sea_radius - 1 else TerrainType.COAST
                resource = ResourceType.FISH if random.random() < 0.2 and terrain == TerrainType.COAST else None
                explored = random.random() < 0.3
                visible = random.random() < 0.2 and explored
            else:
                # 육지 지형 랜덤 선택
                land_terrains = [
                    TerrainType.PLAINS, TerrainType.GRASSLAND, 
                    TerrainType.HILLS, TerrainType.FOREST,
                    TerrainType.DESERT
                ]
                terrain_weights = [0.3, 0.3, 0.15, 0.15, 0.1]  # 지형별 확률
                terrain = random.choices(land_terrains, weights=terrain_weights)[0]
                
                # 자원 배치 (20% 확률)
                if random.random() < 0.2:
                    if terrain == TerrainType.PLAINS:
                        resource = random.choice([ResourceType.WHEAT, ResourceType.HORSES, None, None])
                    elif terrain == TerrainType.GRASSLAND:
                        resource = random.choice([ResourceType.CATTLE, ResourceType.SHEEP, None, None])
                    elif terrain == TerrainType.HILLS:
                        resource = random.choice([ResourceType.IRON, ResourceType.COAL, None, None])
                    elif terrain == TerrainType.FOREST:
                        resource = None
                    elif terrain == TerrainType.DESERT:
                        resource = random.choice([ResourceType.GOLD, None, None])
                    else:
                        resource = None
                else:
                    resource = None
                
                # 가시성/탐험 상태
                distance_from_center = distance - sea_radius
                explored = random.random() < (0.8 - distance_from_center * 0.1)
                visible = random.random() < (0.6 - distance_from_center * 0.1) and explored
            
            # 헥스 타일 생성
            hexagon = HexTile(
                q=q,
                r=r,
                s=s,
                terrain=terrain,
                resource=resource,
                visible=False,  # 기본값: 보이지 않음
                explored=False   # 기본값: 탐험되지 않음
            )
            
            # 문명 시작 위치에 도시와 유닛 배치
            for civ_name, pos in civ_positions.items():
                # 도시 위치
                if q == pos["q"] and r == pos["r"]:
                    hexagon.city_id = pos["city_id"]
                    hexagon.occupant = civ_name
                    hexagon.terrain = TerrainType.PLAINS  # 도시는 평원에 위치
                    # 플레이어(한국)만 초기에 볼 수 있음
                    if civ_name == "Korea":
                        hexagon.visible = True
                        hexagon.explored = True
                    else:
                        hexagon.visible = False
                        hexagon.explored = False
                
                # 유닛 위치
                if q == pos["unit_q"] and r == pos["unit_r"]:
                    hexagon.unit_id = pos["unit_id"]
                    hexagon.occupant = civ_name
                    # 플레이어(한국)만 초기에 볼 수 있음
                    if civ_name == "Korea":
                        hexagon.visible = True
                        hexagon.explored = True
                    else:
                        hexagon.visible = False
                        hexagon.explored = False
            
            # 문명 시작 주변 지형 조정 (평원, 초원, 숲 등으로 적절히 배치)
            for civ_name, pos in civ_positions.items():
                # 도시 근처 타일(2칸 이내)은 적절한 지형으로 설정
                dist_to_city = max(
                    abs(q - pos["q"]), 
                    abs(r - pos["r"]), 
                    abs(s - (-pos["q"] - pos["r"]))
                )
                
                if dist_to_city <= 2 and dist_to_city > 0 and not is_sea and not is_edge:
                    # 랜덤하게 좋은 지형 선택 (평원/초원/숲 등)
                    good_terrains = [
                        TerrainType.PLAINS, TerrainType.GRASSLAND, 
                        TerrainType.FOREST, TerrainType.HILLS
                    ]
                    hexagon.terrain = random.choice(good_terrains)
                    
                    # 좋은 자원도 배치 (20% 확률)
                    if random.random() < 0.2:
                        good_resources = [
                            ResourceType.WHEAT, ResourceType.HORSES, 
                            ResourceType.CATTLE, ResourceType.IRON
                        ]
                        hexagon.resource = random.choice(good_resources)
            
            # 플레이어 위치는 시야 범위가 넓게 탐험됨
            dist_to_player_city = max(
                abs(q - civ_positions["Korea"]["q"]), 
                abs(r - civ_positions["Korea"]["r"]), 
                abs(s - (-civ_positions["Korea"]["q"] - civ_positions["Korea"]["r"]))
            )
            
            dist_to_player_unit = max(
                abs(q - civ_positions["Korea"]["unit_q"]), 
                abs(r - civ_positions["Korea"]["unit_r"]), 
                abs(s - (-civ_positions["Korea"]["unit_q"] - civ_positions["Korea"]["unit_r"]))
            )
            
            # 도시 주변 2칸 이내는 완전히 보임
            if dist_to_player_city <= 2:
                hexagon.visible = True
                hexagon.explored = True
            # 유닛 주변 1칸 이내는 완전히 보임 (도시 시야와 중복되지 않는 경우)
            elif dist_to_player_unit <= 1:
                hexagon.visible = True
                hexagon.explored = True
            # 나머지는 안보임
            else:
                hexagon.visible = False
                # 탐험 여부는 기존 설정 유지 (도시, 유닛 위치는 이미 앞에서 설정됨)
            
            hexagons.append(hexagon)
    
    return hexagons

# 턴 진행 API 엔드포인트 추가
@router.post("/turn/next")
async def next_turn(game_id: str, user_id: str):
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
        
        # 사용자 ID를 정수로 변환
        user_id_int = int(user_id) if user_id and user_id.isdigit() else 1
        
        # 1. 먼저 게임 정보 조회
        game = await prisma.game.find_unique(
            where={"id": game_id}
        )
        
        if not game:
            return {
                "success": False,
                "status_code": 404,
                "message": "해당 게임을 찾을 수 없습니다."
            }
        
        # 게임 소유자 확인 (문자열 비교)
        if game.userId != user_id:
            return {
                "success": False,
                "status_code": 403,
                "message": "해당 게임에 대한 권한이 없습니다."
            }
        
        # 2. 현재 턴 정보로 게임 상태 조회
        current_turn = game.currentTurn
        
        game_states = await prisma.gamestate.find_many(
            where={
                "gameId": game_id,
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
        
        # 다음 턴으로 게임 상태 업데이트 (실제로는 턴 진행 로직 필요)
        # 여기서 AI들의 턴 처리, 자원 생산, 유닛 이동 등의 로직 처리
        
        # 다음 턴 번호
        next_turn_number = current_turn + 1
        
        # 새로운 게임 상태 생성 (이전 상태 복사 후 변경)
        new_state_data = current_state.stateData
        new_state_data["turn"] = next_turn_number
        
        # TODO: 여기서 게임 상태 업데이트 로직 구현
        # (자원 증가, AI 문명 움직임, 등)
        
        # 게임 업데이트
        updated_game = await prisma.game.update(
            where={"id": game_id},
            data={
                "currentTurn": next_turn_number
            }
        )
        
        # 새로운 게임 상태 별도 생성
        await prisma.gamestate.create(
            data={
                "gameId": game_id,
                "turn": next_turn_number,
                "stateData": json.dumps(new_state_data)
            }
        )
    
        
        return {
            "success": True,
            "status_code": 200,
            "message": f"턴 {next_turn_number}로 진행되었습니다.",
            "data": {
                "game_id": game_id,
                "current_turn": next_turn_number,
                "state": new_state_data
            }
        }
        
    except Exception as e:
        # 오류 발생 시 연결 종료
        
        return {
            "success": False,
            "status_code": 500,
            "message": f"턴 진행 중 오류가 발생했습니다: {str(e)}",
            "error": {
                "type": type(e).__name__,
                "detail": str(e)
            }
        }

@router.get("/game/{game_id}")
async def get_game_state(game_id: str, user_id: str, turn: Optional[int] = None):
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
        
        # 사용자 ID를 정수로 변환
        user_id_int = int(user_id) if user_id and user_id.isdigit() else 1
        
        # 게임 존재 여부 확인
        game = await prisma.game.find_unique(
            where={"id": game_id}
        )
        
        if not game:
            return {
                "success": False,
                "status_code": 404,
                "message": "해당 게임을 찾을 수 없습니다."
            }
        
        # 게임 소유자 확인 (문자열 비교)
        if game.userId != user_id:
            return {
                "success": False,
                "status_code": 403,
                "message": "해당 게임에 대한 권한이 없습니다."
            }
        
        # 턴 번호 결정 (지정한 턴 또는 현재 턴)
        query_turn = turn if turn is not None else game.currentTurn
        
        # 게임 상태 조회
        game_state = await prisma.gamestate.find_first(
            where={
                "gameId": game_id,
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
                "game_id": game_id,
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

@router.get("/adjacent")
async def get_adjacent_tiles(q: int, r: int):
    """지정된 타일 주변의 인접 타일 정보 반환"""
    try:
        # 인접 방향 (육각형 그리드)
        directions = [
            (1, 0, -1),  # 동쪽
            (1, -1, 0),  # 북동쪽
            (0, -1, 1),  # 북서쪽
            (-1, 0, 1),  # 서쪽
            (-1, 1, 0),  # 남서쪽
            (0, 1, -1)   # 남동쪽
        ]
        
        hexagons = []
        
        for dir_q, dir_r, dir_s in directions:
            adj_q = q + dir_q
            adj_r = r + dir_r
            adj_s = -adj_q - adj_r
            
            # 랜덤한 지형 생성 (실제로는 데이터베이스에서 조회)
            terrain = random.choice([t for t in TerrainType])
            
            # 바다/산은 제외 (이동 가능한 타일만)
            while terrain in [TerrainType.OCEAN, TerrainType.MOUNTAIN]:
                terrain = random.choice([t for t in TerrainType])
            
            hexagon = HexTile(
                q=adj_q,
                r=adj_r,
                s=adj_s,
                terrain=terrain,
                resource=random.choice([r for r in ResourceType]) if random.random() < 0.2 else None,
                visible=True,
                explored=True
            )
            
            hexagons.append(hexagon)
        
        # 성공 응답 반환
        return {
            "success": True,
            "status_code": 200,
            "message": "인접 타일 정보가 성공적으로 로드되었습니다.",
            "data": {
                "origin": {"q": q, "r": r, "s": -q-r},
                "hexagons": hexagons
            },
            "meta": {
                "count": len(hexagons)
            }
        }
    
    except Exception as e:
        # 오류 로깅 (실제 운영 환경에서는 로깅 시스템 사용)
        
        # 에러 응답 반환
        return {
            "success": False,
            "status_code": 500,
            "message": f"인접 타일 정보 로드 중 오류가 발생했습니다: {str(e)}",
            "error": {
                "type": type(e).__name__,
                "detail": str(e)
            }
        }