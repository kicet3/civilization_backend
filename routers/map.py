from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Dict, Any, Optional
from models.hexmap import HexTile, TerrainType, ResourceType, GameMapState, HexCoord, Civilization
import random
import math
import uuid
from datetime import datetime
import json
import hashlib
from db.client import prisma

router = APIRouter()

@router.post("/init", summary="새 게임 맵 초기화", response_description="초기화된 게임 맵 데이터 반환")
async def initialize_map(user_name: str):
    """새 게임 맵을 초기화하고 데이터베이스에 저장"""
    try:
        # Prisma 연결
        try:
            await prisma.connect()
            print('Connected to Prisma')
        except Exception as e:
            if "Already connected" not in str(e):
                raise e
        
        # 사용자 이름을 SHA256으로 해시
        user_name_hash = hashlib.sha256(user_name.encode()).hexdigest()
        
        # 1. 새 게임 생성
        new_game = await prisma.game.create(
            data={
                "userName": user_name_hash,  # snake_case가 아닌 camelCase 사용
                "mapRadius": 10,
                "turnLimit": 50,
                "createdAt": datetime.now(),
                "year": 1000,  # 1턴의 연도를 1000년으로 세팅
                "currentTurn": 1
            }
        )
        
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
            civ_type = await prisma.civtype.create(
                data={
                    "name": civ["name"],
                    "leaderName": civ["leaderName"],  # leader_name이 아닌 leaderName 사용
                    "personality": civ["personality"]
                }
            )
            created_civ_types.append(civ_type)
        print('Created civilization types')
        
        # 3. 플레이어 문명 생성 (중앙에 위치)
        player_civ = await prisma.gameciv.create(
            data={
                "gameId": new_game.id,  # game_id가 아닌 gameId 사용
                "civTypeId": created_civ_types[0].id,  # civ_type_id가 아닌 civTypeId 사용
                "isPlayer": True,  # is_player가 아닌 isPlayer 사용
                "startQ": 0,  # start_q가 아닌 startQ 사용
                "startR": 0   # start_r가 아닌 startR 사용
            }
        )
        print('Created player civilization')
        
        # 4. AI 문명 생성 (플레이어와 14헥스 이상 거리)
        ai_civs = []
        for i, civ_type in enumerate(created_civ_types[1:], 1):
            # AI 문명의 시작 위치 계산 (플레이어와 14헥스 이상 거리)
            angle = (2 * math.pi * i) / 6  # 6개의 AI 문명을 균등하게 배치
            distance = 15  # 14헥스 이상 거리 확보
            q = int(distance * math.cos(angle))
            r = int(distance * math.sin(angle))
            
            ai_civ = await prisma.gameciv.create(
                data={
                    "gameId": new_game.id,
                    "civTypeId": civ_type.id,
                    "isPlayer": False,
                    "startQ": q,
                    "startR": r
                }
            )
            ai_civs.append(ai_civ)
            print(f'Created AI civilization {civ_type.name} at {q}, {r}')
        
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
                    
                    map_tile = await prisma.maptile.create(
                        data={
                            "gameId": new_game.id,
                            "q": q,
                            "r": r,
                            "terrain": terrain,
                            "resource": resource
                        }
                    )
                    map_tiles.append(map_tile)
        
        # 6. 플레이어 도시 생성
        player_city = await prisma.city.create(
            data={
                "gameCivId": player_civ.id,  # game_civ_id가 아닌 gameCivId 사용
                "name": "서울",
                "q": 0,
                "r": 0,
                "population": 1,
                "createdTurn": 1,  # created_turn이 아닌 createdTurn 사용
                "food": 20,        # 초기 식량 20
                "production": 10    # 초기 생산력 10
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
                    "createdTurn": 1,
                    "food": 20,
                    "production": 10
                }
            )
        
        # 문명 초기 자원 설정
        await prisma.gameciv.update(
            where={"id": player_civ.id},
            data={
                "gold": 30,
                "science": 5,
                "culture": 0
            }
        )
        
        # AI 문명 초기 자원 설정
        for ai_civ in ai_civs:
            await prisma.gameciv.update(
                where={"id": ai_civ.id},
                data={
                    "gold": 30,
                    "science": 5,
                    "culture": 0
                }
            )
        
        # 8. 초기 유닛 생성
        # 플레이어 문명 시작 유닛 생성
        # 초기 전사 유닛 (근접 유닛)
        initial_warrior = await prisma.unittype.find_first(
            where={
                "category": "Melee",
                "era": "Medieval"
            }
        )
        
        if initial_warrior:
            await prisma.gameunit.create(
                data={
                    "gameCivId": player_civ.id,
                    "unitTypeId": initial_warrior.id,
                    "q": 0,  # 도시 위치와 동일
                    "r": 0,
                    "hp": 100,
                    "createdTurn": 1,
                    "moved": False
                }
            )
        
        # 초기 정찰병 (정찰 유닛)
        initial_scout = await prisma.unittype.find_first(
            where={
                "category": "Civilian",
                "era": "Medieval"
            }
        )
        
        if initial_scout:
            await prisma.gameunit.create(
                data={
                    "gameCivId": player_civ.id,
                    "unitTypeId": initial_scout.id,
                    "q": 0,  # 도시 위치와 동일
                    "r": 0,
                    "hp": 100,
                    "createdTurn": 1,
                    "moved": False
                }
            )
        
        # AI 문명 시작 유닛 생성
        for ai_civ in ai_civs:
            # AI 전사 유닛
            if initial_warrior:
                await prisma.gameunit.create(
                    data={
                        "gameCivId": ai_civ.id,
                        "unitTypeId": initial_warrior.id,
                        "q": ai_civ.startQ,  # AI 도시 위치와 동일
                        "r": ai_civ.startR,
                        "hp": 100,
                        "createdTurn": 1,
                        "moved": False
                    }
                )
            
            # AI 정찰병 유닛 (50% 확률로 생성)
            if initial_scout and random.random() < 0.5:
                await prisma.gameunit.create(
                    data={
                        "gameCivId": ai_civ.id,
                        "unitTypeId": initial_scout.id,
                        "q": ai_civ.startQ,  # AI 도시 위치와 동일
                        "r": ai_civ.startR,
                        "hp": 100,
                        "createdTurn": 1,
                        "moved": False
                    }
                )
        
        # 9. 기술 트리 선택 (플레이어)
        await prisma.treeselection.create(
            data={
                "gameCivId": player_civ.id,
                "treeType": "군사",  # tree_type이 아닌 treeType 사용
                "isMain": True  # is_main이 아닌 isMain 사용
            }
        )
        
        # 8-1. 초기 기술 설정 (첫 시대의 기술들을 available 상태로 설정)
        # 첫 시대(Medieval) 기술 조회
        initial_techs = await prisma.technology.find_many(
            where={
                "era": "Medieval"
            }
        )
        
        # 각 기술을 available 상태로 설정
        for tech in initial_techs:
            await prisma.gamecivtechnology.create(
                data={
                    "gameCivId": player_civ.id,
                    "techId": tech.id,
                    "status": "available",
                    "progressPoints": 0
                }
            )
        
        # AI 문명에도 동일하게 적용
        for ai_civ in ai_civs:
            for tech in initial_techs:
                await prisma.gamecivtechnology.create(
                    data={
                        "gameCivId": ai_civ.id,
                        "techId": tech.id,
                        "status": "available",
                        "progressPoints": 0
                    }
                )
        
        # 9. 턴 스냅샷 생성
        # 플레이어 도시 주변 시야 계산 (2헥스 범위)
        city_sight_range = 2
        visible_tiles = set()
        visible_tiles.add((0, 0))  # 플레이어 도시 위치
        
        # 도시 주변 타일 추가
        for q_offset in range(-city_sight_range, city_sight_range + 1):
            for r_offset in range(max(-city_sight_range, -q_offset - city_sight_range), 
                                min(city_sight_range, -q_offset + city_sight_range) + 1):
                visible_tiles.add((q_offset, r_offset))
        
        # 시야 정보가 포함된 초기 맵 상태
        initial_observed_tiles = [
            {"q": t.q, "r": t.r, "terrain": t.terrain, "resource": t.resource}
            for t in map_tiles if (t.q, t.r) in visible_tiles
        ]
        
        # 초기 게임 상태 데이터 생성
        initial_state_data = {
            "turn": 1,
            "year": 1000,  # 게임 시작 연도
            "era": "Medieval",
            "player_civ": {
                "id": player_civ.id,
                "name": created_civ_types[0].name,
                "leader": created_civ_types[0].leaderName
            },
            "cities": [],  # 빈 초기 도시 목록 (나중에 업데이트됨)
            "units": [],   # 빈 초기 유닛 목록 (나중에 업데이트됨)
            "resources": {
                "gold": 30,
                "science": 5,
                "culture": 0,
                "food": 20,
                "production": 10
            }
        }
        
        # 플레이어 재화 정보
        player_resources = {
            "gold": 30,
            "science": 5,
            "culture": 0,
            "food": 20,
            "production": 10
        }
        
        # TurnSnapshot 생성
        try:
            turn_snapshot = await prisma.turnsnapshot.create(
                data={
                    "gameId": new_game.id,
                    "turnNumber": 1,
                    "civId": player_civ.id,
                    "observedMap": json.dumps({"tiles": initial_observed_tiles}),
                    "researchState": json.dumps({"current": None, "queue": []}),
                    "productionState": json.dumps({"current": None, "queue": []}),
                    "diplomacyState": json.dumps({"relations": {}}),
                    "resourceState": json.dumps({
                        "gold": 30,
                        "science": 20,
                        "food": 30,
                        "production": 20,
                        "culture": 0
                    }),
                    "stateData": initial_state_data,
                    "playerResources": player_resources
                }
            )
            print(f"TurnSnapshot 생성 성공: ID {turn_snapshot.id}, 게임 ID {new_game.id}")
        except Exception as e:
            print(f"TurnSnapshot 생성 오류: {str(e)}")
            # 오류 세부 정보 출력
            import traceback
            traceback.print_exc()
            
            # TurnSnapshot 생성 실패 시 다시 시도 (기본 필수 필드만)
            try:
                simplified_snapshot = await prisma.turnsnapshot.create(
                    data={
                        "gameId": new_game.id,
                        "turnNumber": 1,
                        "civId": player_civ.id,
                        "observedMap": "{}",
                        "researchState": "{}",
                        "productionState": "{}",
                        "diplomacyState": "{}"
                    }
                )
                print(f"기본 TurnSnapshot 생성 성공: ID {simplified_snapshot.id}, 게임 ID {new_game.id}")
            except Exception as e2:
                print(f"기본 TurnSnapshot 생성도 실패: {str(e2)}")
                traceback.print_exc()
                print(f"TurnSnapshot 생성 실패했지만 계속 진행합니다. 게임 ID: {new_game.id}")
                # 이 경우 게임 상태 조회 시 오류가 발생할 수 있음
        
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
                "tileCount": len(map_tiles),
                "year": 1000,  # 1턴의 연도 정보 반환
                "turn": 1
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
        turn_snapshots = await prisma.turnsnapshot.find_many(
            where={
                "gameId": game_id,
            }
        )
        
        # 턴 스냅샷이 없는 경우 초기 턴 스냅샷 생성
        if not turn_snapshots:
            print(f"게임 ID {game_id}에 대한 턴 스냅샷이 없습니다. 초기 스냅샷 생성 시도...")
            
            # 플레이어 문명 찾기
            player_civ = await prisma.gameciv.find_first(
                where={
                    "gameId": game_id,
                    "isPlayer": True
                }
            )
            
            if not player_civ:
                return {
                    "success": False,
                    "status_code": 404,
                    "message": "플레이어 문명을 찾을 수 없습니다."
                }
            
            # 맵 타일 조회
            map_tiles = await prisma.maptile.find_many(
                where={
                    "gameId": game_id
                }
            )
            
            # 플레이어 도시 주변 시야 계산 (2헥스 범위)
            city_sight_range = 2
            visible_tiles = set()
            
            # 플레이어 도시 찾기
            player_cities = await prisma.city.find_many(
                where={
                    "gameCivId": player_civ.id
                }
            )
            
            # 도시 위치 기준 시야 계산
            for city in player_cities:
                visible_tiles.add((city.q, city.r))
                
                for q_offset in range(-city_sight_range, city_sight_range + 1):
                    for r_offset in range(max(-city_sight_range, -q_offset - city_sight_range), 
                                         min(city_sight_range, -q_offset + city_sight_range) + 1):
                        visible_tiles.add((city.q + q_offset, city.r + r_offset))
            
            # 시야 정보가 포함된 초기 맵 상태
            initial_observed_tiles = [
                {"q": t.q, "r": t.r, "terrain": t.terrain, "resource": t.resource}
                for t in map_tiles if (t.q, t.r) in visible_tiles
            ]
            
            # 초기 게임 상태 데이터 생성
            initial_state_data = {
                "turn": 1,
                "year": 1000,  # 게임 시작 연도
                "era": "Medieval",
                "player_civ": {
                    "id": player_civ.id,
                    "name": player_civ.name,
                    "leader": player_civ.leaderName
                },
                "cities": [],  # 빈 초기 도시 목록
                "units": []    # 빈 초기 유닛 목록
            }
            
            # 플레이어 재화 정보
            player_resources = {
                "gold": player_civ.gold,
                "science": player_civ.science,
                "culture": player_civ.culture,
                "food": player_civ.food,  # 기본값
                "production": player_civ.production  # 기본값
            }
            
            # 도시 정보로 food/production 업데이트
            total_food = 0
            total_production = 0
            
            for city in player_cities:
                total_food += city.food
                total_production += city.production
            
            if player_cities:
                player_resources["food"] = total_food
                player_resources["production"] = total_production
            
            # 초기 턴 스냅샷 생성
            try:
                new_snapshot = await prisma.turnsnapshot.create(
                    data={
                        "gameId": game_id,
                        "turnNumber": 1,
                        "civId": player_civ.id,
                        "observedMap": json.dumps({"tiles": initial_observed_tiles}),
                        "researchState": json.dumps({"current": None, "queue": []}),
                        "productionState": json.dumps({"current": None, "queue": []}),
                        "diplomacyState": json.dumps({"relations": {}}),
                        "resourceState": json.dumps(player_resources),
                        "stateData": initial_state_data,
                        "playerResources": player_resources
                    }
                )
                print(f"게임 ID {game_id}에 대한 초기 턴 스냅샷 생성 성공: ID {new_snapshot.id}")
                turn_snapshots = [new_snapshot]
            except Exception as e:
                print(f"초기 턴 스냅샷 생성 실패: {str(e)}")
                # 다시 시도 (간소화된 버전)
                try:
                    simple_snapshot = await prisma.turnsnapshot.create(
                        data={
                            "gameId": game_id,
                            "turnNumber": 1,
                            "civId": player_civ.id,
                            "observedMap": "{}",
                            "researchState": "{}",
                            "productionState": "{}",
                            "diplomacyState": "{}"
                        }
                    )
                    print(f"간소화된 초기 턴 스냅샷 생성 성공: ID {simple_snapshot.id}")
                    turn_snapshots = [simple_snapshot]
                except Exception as e2:
                    print(f"간소화된 초기 턴 스냅샷 생성도 실패: {str(e2)}")
                    return {
                        "success": False,
                        "status_code": 500,
                        "message": f"턴 스냅샷 생성 중 오류가 발생했습니다: {str(e2)}",
                        "error": {
                            "type": type(e2).__name__,
                            "detail": str(e2)
                        }
                    }
        
        # 가장 높은 턴 번호를 가진 스냅샷 찾기
        turn_snapshot = max(turn_snapshots, key=lambda x: x.turnNumber)
        
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
        
        # 플레이어 문명 찾기
        player_civ = next((civ for civ in game_civs if civ.isPlayer), None)
        
        # 시야 범위 계산 (플레이어의 도시와 유닛 주변)
        visible_tiles = set()
        explored_tiles = set()
        
        # 턴 스냅샷에서 이전에 탐색한 타일 정보 가져오기
        try:
            observed_map = json.loads(turn_snapshot.observedMap)
            if isinstance(observed_map, dict) and "tiles" in observed_map:
                for tile_data in observed_map["tiles"]:
                    explored_tiles.add((tile_data["q"], tile_data["r"]))
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            # 오류 발생 시 로그만 남기고 진행 (빈 explored_tiles 사용)
            print(f"맵 상태 파싱 오류: {str(e)}")
        
        if player_civ:
            # 도시 시야 범위 (2 헥스로 변경)
            city_sight_range = 2
            for city in player_civ.cities:
                # 도시 위치 자체도 추가
                visible_tiles.add((city.q, city.r))
                
                # 도시 주변 타일 추가
                for q_offset in range(-city_sight_range, city_sight_range + 1):
                    for r_offset in range(max(-city_sight_range, -q_offset - city_sight_range), 
                                         min(city_sight_range, -q_offset + city_sight_range) + 1):
                        visible_tiles.add((city.q + q_offset, city.r + r_offset))
            
            # 유닛 시야 범위 (일반적으로 2 헥스, 유닛 타입에 따라 다를 수 있음)
            for unit in player_civ.units:
                # 기본 시야 범위
                unit_sight_range = 2
                
                # 유닛 위치 자체도 추가
                visible_tiles.add((unit.q, unit.r))
                
                # 유닛 주변 타일 추가
                for q_offset in range(-unit_sight_range, unit_sight_range + 1):
                    for r_offset in range(max(-unit_sight_range, -q_offset - unit_sight_range), 
                                         min(unit_sight_range, -q_offset + unit_sight_range) + 1):
                        visible_tiles.add((unit.q + q_offset, unit.r + r_offset))
        
        # 시야 정보를 포함한 타일 정보 생성
        game_state = {
            "tiles": [
                {
                    "q": tile.q,
                    "r": tile.r,
                    "terrain": tile.terrain,
                    "resource": tile.resource,
                    "exploration": "visible" if (tile.q, tile.r) in visible_tiles else
                                  "explored" if (tile.q, tile.r) in explored_tiles else 
                                  "unexplored"
                } for tile in map_tiles
            ],
            "civs": [
                {
                    "id": civ.id,
                    "name": civ.civType.name,
                    "isPlayer": civ.isPlayer,
                    "gold": civ.gold,
                    "science": civ.science,
                    "culture": civ.culture,
                    "cities": [
                        {
                            "id": city.id,
                            "name": city.name,
                            "q": city.q,
                            "r": city.r,
                            "population": city.population,
                            "food": city.food,
                            "production": city.production
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
        
        # TurnSnapshot에서 플레이어 재화 정보 가져오기
        try:
            player_resources = getattr(turn_snapshot, 'playerResources', None)
        except AttributeError:
            # playerResources 속성이 없는 경우
            player_resources = None
        
        # 플레이어 재화 정보가 없는 경우 계산
        if not player_resources and player_civ:
            # 플레이어 도시들의 식량과 생산력 정보 계산
            total_food = 0
            total_production = 0
            
            for city in player_civ.cities:
                total_food += city.food
                total_production += city.production
            
            # 플레이어 재화 정보 구성
            player_resources = {
                "gold": player_civ.gold,
                "science": player_civ.science,
                "culture": player_civ.culture,
                "food": total_food,
                "production": total_production
            }
            
            # TurnSnapshot 업데이트 시도 - 에러 무시
            try:
                await prisma.turnsnapshot.update(
                    where={"id": turn_snapshot.id},
                    data={"playerResources": player_resources}
                )
            except Exception as update_error:
                print(f"TurnSnapshot 업데이트 중 오류: {str(update_error)}")
        
        return {
            "success": True,
            "status_code": 200,
            "message": f"턴 {turn_snapshot.turnNumber}의 게임 상태를 조회했습니다.",
            "data": game_state,
            "player_resources": player_resources,
            "meta": {
                "game_id": game_id,
                "turn": turn_snapshot.turnNumber,
                "year": turn_snapshot.year,
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
                    "resource": tile.resource
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