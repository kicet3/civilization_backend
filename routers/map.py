from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Dict, Any, Optional
from models.hexmap import HexTile, TerrainType, ResourceType, GameMapState, HexCoord, Civilization
import random
import math
import uuid
from datetime import datetime
import json
import hashlib
from client import prisma

router = APIRouter()

@router.post("/init", summary="새 게임 맵 초기화", response_description="초기화된 게임 맵 데이터 반환")
async def initialize_map(user_name: str):
    """새 게임 맵을 초기화하고 데이터베이스에 저장"""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
            print('a')
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 사용자 이름을 SHA256으로 해시
        user_name_hash = hashlib.sha256(user_name.encode()).hexdigest()
        
        # 1. 새 게임 생성
        new_game = await prisma.game.create(
            data={
                "userName": user_name_hash,
                "mapRadius": 10,
                "turnLimit": 50,
                "createdAt": datetime.now()
            }
        )
        print('b')
        # 2. 문명 타입 생성 (7개 문명)
        civ_types = [
            {"name": "한국", "leaderName": "세종대왕", "personality": "Diplomat"},
            {"name": "일본", "leaderName": "오다 노부나가", "personality": "Warlike"},
            {"name": "중국", "leaderName": "무측천", "personality": "Diplomat"},
            {"name": "몽골", "leaderName": "칭기스 칸", "personality": "Warlike"},
            {"name": "러시아", "leaderName": "예카테리나", "personality": "Trader"},
            {"name": "로마", "leaderName": "아우구스투스", "personality": "Warlike"},
            {"name": "이집트", "leaderName": "클레오파트라", "personality": "Trader"}
        ]
        
        created_civ_types = []
        for civ in civ_types:
            civ_type = await prisma.civtype.create(  # CivType -> civtype
                data={
                    "name": civ["name"],
                    "leaderName": civ["leaderName"],
                    "personality": civ["personality"]
                }
            )
            created_civ_types.append(civ_type)
        print('c')
        # 3. 플레이어 문명 생성 (중앙에 위치)
        player_civ = await prisma.gameciv.create(  # GameCiv -> gameciv
            data={
                "gameId": new_game.id,
                "civTypeId": created_civ_types[0].id,  # 한국
                "isPlayer": True,
                "startQ": 0,
                "startR": 0
            }
        )
        print('a')
        # 4. AI 문명 생성 (플레이어와 14헥스 이상 거리)
        ai_civs = []
        for i, civ_type in enumerate(created_civ_types[1:], 1):
            # AI 문명의 시작 위치 계산 (플레이어와 14헥스 이상 거리)
            angle = (2 * math.pi * i) / 6  # 6개의 AI 문명을 균등하게 배치
            distance = 15  # 14헥스 이상 거리 확보
            q = int(distance * math.cos(angle))
            r = int(distance * math.sin(angle))
            
            ai_civ = await prisma.gameciv.create(  # GameCiv -> gameciv
                data={
                    "gameId": new_game.id,
                    "civTypeId": civ_type.id,
                    "isPlayer": False,
                    "startQ": q,
                    "startR": r
                }
            )
            ai_civs.append(ai_civ)
        
        # 5. 맵 타일 생성 (반경 10의 육각형 맵)
        map_tiles = []
        for q in range(-10, 11):
            for r in range(-10, 11):
                # 육각형 좌표 제약 조건: |q| + |r| + |s| ≤ 10
                s = -q - r
                if abs(q) + abs(r) + abs(s) <= 20:  # 반경 10의 육각형
                    # 지형 랜덤 생성
                    terrain_types = ["Plains", "Grassland", "Hills", "Forest", "Desert", "Mountain"]
                    terrain = random.choice(terrain_types)
                    
                    # 자원 랜덤 생성 (20% 확률)
                    resource = "NoResource"  # 기본값
                    if random.random() < 0.2:
                        resource_types = ["Food", "Production", "Gold", "Science"]
                        resource = random.choice(resource_types)
                    
                    # Prisma enum 값으로 변환
                    resource_enum = getattr(prisma.ResourceType, resource)
                    
                    map_tile = await prisma.maptile.create(  # MapTile -> maptile
                        data={
                            "gameId": new_game.id,
                            "q": q,
                            "r": r,
                            "terrain": terrain,
                            "resource": resource_enum
                        }
                    )
                    map_tiles.append(map_tile)
        
        # 6. 플레이어 도시 생성
        player_city = await prisma.city.create(
            data={
                "gameCivId": player_civ.id,
                "name": "서울",
                "q": 0,
                "r": 0,
                "population": 1,
                "createdTurn": 1
            }
        )
        
        # 7. AI 도시 생성
        ai_city_names = ["도쿄", "베이징", "울란바토르", "모스크바", "로마", "알렉산드리아"]
        for i, ai_civ in enumerate(ai_civs):
            await prisma.city.create(
                data={
                    "gameCivId": ai_civ.id,
                    "name": ai_city_names[i],
                    "q": ai_civ.startQ,
                    "r": ai_civ.startR,
                    "population": 1,
                    "createdTurn": 1
                }
            )
        
        # 8. 기술 트리 선택 (플레이어)
        await prisma.treeselection.create(  # TreeSelection -> treeselection
            data={
                "gameCivId": player_civ.id,
                "treeType": "군사",
                "isMain": True
            }
        )
        
        # 9. 턴 스냅샷 생성
        await prisma.turnsnapshot.create(  # TurnSnapshot -> turnsnapshot
            data={
                "gameId": new_game.id,
                "turnNumber": 1,
                "civId": player_civ.id,
                "observedMap": {"tiles": [{"q": t.q, "r": t.r, "terrain": t.terrain, "resource": t.resource.value} for t in map_tiles]},
                "researchState": {"current": None, "queue": []},
                "productionState": {"current": None, "queue": []},
                "diplomacyState": {"relations": {}}
            }
        )
        
        # 성공 응답 반환
        return {
            "success": True,
            "status_code": 200,
            "message": "새 게임 맵이 성공적으로 초기화되었습니다.",
            "data": {
                "game_id": new_game.id,
                "userName": user_name,  # 원본 사용자 이름 반환
                "mapRadius": new_game.mapRadius,
                "turnLimit": new_game.turnLimit,
                "player_civ_id": player_civ.id,
                "ai_civ_ids": [civ.id for civ in ai_civs],
                "tileCount": len(map_tiles)
            },
            "createdAt": new_game.createdAt.isoformat()
        }
        
    except Exception as e:
        # 오류 발생 시 연결 종료
        return {
            "success": False,
            "status_code": 500,
            "message": f"맵 초기화 중 오류가 발생했습니다: {str(e)}",
            "error": {
                "type": type(e).__name__,
                "detail": str(e)
            }
        }

@router.get("/data", summary="맵 데이터 조회", response_description="맵 데이터 반환")
async def get_map_data(game_id: Optional[int] = Query(None, description="게임 ID")):
    """게임 맵 데이터 반환"""
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
        
        # 게임 ID가 제공되지 않은 경우
        if not game_id:
            return {
                "success": False,
                "status_code": 400,
                "message": "게임 ID가 필요합니다."
            }
        
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
        
        # 최신 턴 스냅샷 조회
        turn_snapshot = await prisma.turnsnapshot.find_first(
            where={
                "gameId": game_id,
                "turnNumber": 1  # 또는 현재 턴 조회 로직 추가
            },
            order_by={
                "turnNumber": "desc"
            }
        )
        
        if not turn_snapshot:
            return {
                "success": False,
                "status_code": 404,
                "message": f"게임 상태를 찾을 수 없습니다."
            }
        
        # 맵 타일 조회
        map_tiles = await prisma.maptile.find_many(
            where={
                "gameId": game_id
            }
        )
        
        # 문명 정보 조회
        game_civs = await prisma.gameciv.find_many(
            where={
                "gameId": game_id
            },
            include={
                "civType": True,
                "cities": True,
                "units": True
            }
        )
        
        # 게임 상태 구성
        game_state = {
            "tiles": [
                {
                    "q": tile.q,
                    "r": tile.r,
                    "terrain": tile.terrain,
                    "resource": tile.resource.value
                } for tile in map_tiles
            ],
            "civs": [
                {
                    "id": civ.id,
                    "name": civ.civType.name,
                    "isPlayer": civ.isPlayer,
                    "cities": [
                        {
                            "id": city.id,
                            "name": city.name,
                            "q": city.q,
                            "r": city.r,
                            "population": city.population
                        } for city in civ.cities
                    ],
                    "units": [
                        {
                            "id": unit.id,
                            "typeId": unit.unitTypeId,
                            "q": unit.q,
                            "r": unit.r,
                            "hp": unit.hp
                        } for unit in civ.units
                    ]
                } for civ in game_civs
            ],
            "currentTurn": turn_snapshot.turnNumber
        }
        
        return {
            "success": True,
            "status_code": 200,
            "message": f"턴 {turn_snapshot.turnNumber}의 게임 상태를 조회했습니다.",
            "data": game_state,
            "meta": {
                "game_id": game_id,
                "turn": turn_snapshot.turnNumber,
                "createdAt": turn_snapshot.createdAt.isoformat()
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
async def get_adjacent_tiles(q: int, r: int, game_id: int):
    """지정된 타일 주변의 인접 타일 정보 반환"""
    try:
        # 연결 확인
        try:
            await prisma.connect()
        except Exception as e:
            
            if "Already connected" not in str(e):
                raise e
        
        # 인접 방향 (육각형 그리드)
        directions = [
            (1, 0, -1),  # 동쪽
            (1, -1, 0),  # 북동쪽
            (0, -1, 1),  # 북서쪽
            (-1, 0, 1),  # 서쪽
            (-1, 1, 0),  # 남서쪽
            (0, 1, -1)   # 남동쪽
        ]
        
        adjacent_tiles = []
        
        for dir_q, dir_r, dir_s in directions:
            adj_q = q + dir_q
            adj_r = r + dir_r
            
            # 데이터베이스에서 실제 타일 조회
            tile = await prisma.maptile.find_first(
                where={
                    "gameId": game_id,
                    "q": adj_q,
                    "r": adj_r
                }
            )
            
            if tile:
                adjacent_tiles.append({
                    "q": tile.q,
                    "r": tile.r,
                    "s": -tile.q - tile.r,
                    "terrain": tile.terrain,
                    "resource": tile.resource.value
                })
        
        # 성공 응답 반환
        return {
            "success": True,
            "status_code": 200,
            "message": "인접 타일 정보가 성공적으로 로드되었습니다.",
            "data": {
                "origin": {"q": q, "r": r, "s": -q-r},
                "hexagons": adjacent_tiles
            },
            "meta": {
                "count": len(adjacent_tiles)
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "message": f"인접 타일 정보 로드 중 오류가 발생했습니다: {str(e)}",
            "error": {
                "type": type(e).__name__,
                "detail": str(e)
            }
        }