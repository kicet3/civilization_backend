from langchain.tools import BaseTool
import httpx
import json
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class GameAPITool(BaseTool):
    name = "game_api"
    description = "게임 상태 조회/업데이트용 HTTP API 호출"
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__()
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
    
    async def _arun(self, query: str) -> str:
        """API 비동기 호출"""
        try:
            # 쿼리 파싱
            cmd_parts = query.split(maxsplit=1)
            if len(cmd_parts) < 1:
                return json.dumps({"error": "명령어가 지정되지 않았습니다."})
            
            command = cmd_parts[0]
            params = cmd_parts[1] if len(cmd_parts) > 1 else ""
            
            # 명령어별 API 호출
            if command == "get_state":
                return await self._get_game_state(params)
            elif command == "get_cities":
                return await self._get_cities(params)
            elif command == "get_city":
                return await self._get_city_detail(params)
            elif command == "get_production":
                return await self._get_production_queue(params)
            elif command == "apply_actions":
                return await self._apply_actions(params)
            else:
                return json.dumps({"error": f"알 수 없는 명령어: {command}"})
        
        except Exception as e:
            logger.error(f"API 호출 중 오류 발생: {str(e)}")
            return json.dumps({"error": str(e)})
    
    def _run(self, query: str) -> str:
        """동기식 호출 - 실제로는 비동기를 실행하기 위한 래퍼"""
        import asyncio
        return asyncio.run(self._arun(query))
    
    async def _get_game_state(self, params: str) -> str:
        """게임 상태 조회"""
        try:
            game_id = self._extract_param(params, "game_id")
            if not game_id:
                return json.dumps({"error": "game_id가 필요합니다."})
            
            response = await self.client.get(f"/game/state?gameId={game_id}")
            response.raise_for_status()
            return response.text
        except Exception as e:
            return json.dumps({"error": f"게임 상태 조회 실패: {str(e)}"})
    
    async def _get_cities(self, params: str) -> str:
        """도시 목록 조회"""
        try:
            game_id = self._extract_param(params, "game_id")
            player_id = self._extract_param(params, "player_id")
            
            if not game_id:
                return json.dumps({"error": "game_id가 필요합니다."})
            
            url = f"/city/{game_id}/cities"
            if player_id:
                url += f"?player_id={player_id}"
            
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            return json.dumps({"error": f"도시 목록 조회 실패: {str(e)}"})
    
    async def _get_city_detail(self, params: str) -> str:
        """도시 상세 정보 조회"""
        try:
            game_id = self._extract_param(params, "game_id")
            city_id = self._extract_param(params, "city_id")
            
            if not game_id or not city_id:
                return json.dumps({"error": "game_id와 city_id가 필요합니다."})
            
            response = await self.client.get(f"/city/{game_id}/city/{city_id}")
            response.raise_for_status()
            return response.text
        except Exception as e:
            return json.dumps({"error": f"도시 정보 조회 실패: {str(e)}"})
    
    async def _get_production_queue(self, params: str) -> str:
        """도시 생산 큐 조회"""
        try:
            game_id = self._extract_param(params, "game_id")
            city_id = self._extract_param(params, "city_id")
            
            if not game_id or not city_id:
                return json.dumps({"error": "game_id와 city_id가 필요합니다."})
            
            response = await self.client.get(f"/city/{game_id}/city/{city_id}/production")
            response.raise_for_status()
            return response.text
        except Exception as e:
            return json.dumps({"error": f"생산 큐 조회 실패: {str(e)}"})
    
    async def _apply_actions(self, params: str) -> str:
        """액션 적용"""
        try:
            # 파라미터에서 game_id와 action_data 추출
            parts = params.split(" ", 1)
            if len(parts) < 2:
                return json.dumps({"error": "game_id와 action_data가 필요합니다."})
            
            game_id = parts[0]
            action_data = parts[1]
            
            # JSON 문자열을 Python 객체로 변환
            try:
                actions = json.loads(action_data)
            except json.JSONDecodeError:
                return json.dumps({"error": "유효하지 않은 JSON 형식입니다."})
            
            # 각 액션 처리
            results = []
            for action in actions:
                action_type = action.get("type")
                
                if action_type == "production":
                    # 생산 액션 처리
                    result = await self._add_to_production_queue(
                        game_id=game_id,
                        city_id=action.get("cityId"),
                        item_type=action.get("itemType"),
                        item_id=action.get("itemId")
                    )
                    results.append(result)
                # 기타 액션 타입 추가 가능
            
            return json.dumps({"results": results})
        except Exception as e:
            return json.dumps({"error": f"액션 적용 실패: {str(e)}"})
    
    async def _add_to_production_queue(self, game_id: str, city_id: str, item_type: str, item_id: str) -> Dict[str, Any]:
        """생산 큐에 아이템 추가"""
        try:
            request_data = {
                "gameId": game_id,
                "cityId": city_id,
                "itemType": item_type,
                "itemId": item_id
            }
            
            response = await self.client.post(
                f"/city/{game_id}/city/{city_id}/production",
                json=request_data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"생산 큐 아이템 추가 실패: {str(e)}")
            return {"error": str(e)}
    
    def _extract_param(self, params: str, key: str) -> Optional[str]:
        """파라미터 문자열에서 특정 키의 값 추출"""
        import re
        match = re.search(f"{key}=([^ ]+)", params)
        return match.group(1) if match else None 