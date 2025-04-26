from langchain.tools import BaseTool
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.docstore.document import Document
import os
import json
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# 환경변수에서 API 키 가져오기 (없으면 기본값 사용)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")

class VectorRetrievalTool(BaseTool):
    name = "vector_search"
    description = "게임 공략 및 어드바이스 검색용 벡터 검색"
    
    def __init__(self, index_path: str = "./vector_data"):
        super().__init__()
        self.index_path = index_path
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        self.vector_store = None
        
        # 사전 정의된 게임 데이터 (실제로는 문서로부터 로드)
        self.game_data = {
            "units": self._load_unit_data(),
            "buildings": self._load_building_data(),
            "technologies": self._load_technology_data(),
            "eras": self._load_era_data()
        }
        
        # 벡터 스토어 초기화
        self._initialize_vector_store()
    
    def _initialize_vector_store(self):
        """벡터 스토어 초기화"""
        try:
            # 기존 인덱스 로드 시도
            if os.path.exists(f"{self.index_path}/index.faiss"):
                self.vector_store = FAISS.load_local(
                    self.index_path,
                    self.embeddings
                )
                logger.info(f"기존 FAISS 인덱스를 로드했습니다: {self.index_path}")
            else:
                # 인덱스가 없으면 새로 생성
                self._create_vector_store()
        except Exception as e:
            logger.error(f"벡터 스토어 초기화 중 오류 발생: {str(e)}")
            # 오류 발생 시 새로 생성
            self._create_vector_store()
    
    def _create_vector_store(self):
        """벡터 스토어 생성"""
        try:
            # 게임 데이터로부터 문서 생성
            documents = []
            
            # 유닛 데이터
            for unit in self.game_data["units"]:
                content = f"""
                유닛 이름: {unit['name']}
                유닛 ID: {unit['id']}
                종류: {unit['category']}
                시대: {unit['era']}
                생산 비용: {unit['productionCost']}
                전투력: {unit.get('combat_strength', 'N/A')}
                이동력: {unit.get('move', 'N/A')}
                특성: {unit.get('description', '없음')}
                """
                documents.append(Document(
                    page_content=content,
                    metadata={"type": "unit", "id": unit["id"]}
                ))
            
            # 건물 데이터
            for building in self.game_data["buildings"]:
                content = f"""
                건물 이름: {building['name']}
                건물 ID: {building['id']}
                시대: {building['era']}
                생산 비용: {building['productionCost']}
                효과: {building.get('description', '정보 없음')}
                """
                documents.append(Document(
                    page_content=content,
                    metadata={"type": "building", "id": building["id"]}
                ))
            
            # 시대 정보
            for era in self.game_data["eras"]:
                content = f"""
                시대: {era['name']}
                ID: {era['id']}
                특징: {era.get('description', '정보 없음')}
                """
                documents.append(Document(
                    page_content=content,
                    metadata={"type": "era", "id": era["id"]}
                ))
            
            # 추천 생산 전략
            production_strategies = [
                {
                    "name": "초반 도시 확장 전략",
                    "description": "개척자(Settler)를 우선 생산하여 빠르게 영토를 확장하는 전략입니다. 적절한 위치에 도시를 건설해 자원과 타일을 확보하세요.",
                    "era": "고대",
                    "recommended_items": ["settler", "warrior", "granary"]
                },
                {
                    "name": "초반 군사 확장 전략",
                    "description": "전사(Warrior)와 궁수(Archer)를 우선 생산하여 주변 도시국가나 야만인을 정복하는 전략입니다.",
                    "era": "고대",
                    "recommended_items": ["warrior", "archer", "barracks"]
                },
                {
                    "name": "과학 중심 전략",
                    "description": "도서관(Library)과 대학(University)을 우선 건설하여 과학 발전에 집중하는 전략입니다.",
                    "era": "고전/중세",
                    "recommended_items": ["library", "university", "observatory"]
                },
                {
                    "name": "경제 중심 전략",
                    "description": "시장(Market)과 은행(Bank)을 우선 건설하여 경제 발전에 집중하는 전략입니다.",
                    "era": "중세/르네상스",
                    "recommended_items": ["market", "bank", "workshop"]
                },
                {
                    "name": "종교 중심 전략",
                    "description": "신전(Temple)과 대성당(Cathedral)을 우선 건설하여 종교 영향력을 확장하는 전략입니다.",
                    "era": "고전/중세",
                    "recommended_items": ["shrine", "temple", "monastery"]
                },
                {
                    "name": "문화 중심 전략",
                    "description": "기념비(Monument)와 극장(Theatre)을 우선 건설하여 문화 발전에 집중하는 전략입니다.",
                    "era": "고전/르네상스",
                    "recommended_items": ["monument", "amphitheater", "theatre"]
                },
                {
                    "name": "방어 중심 전략",
                    "description": "성벽(Walls)과 성(Castle)을 우선 건설하여 도시 방어에 집중하는 전략입니다.",
                    "era": "고전/중세",
                    "recommended_items": ["walls", "castle", "pikeman"]
                },
                {
                    "name": "생산 중심 전략",
                    "description": "제분소(Mill)와 대장간(Forge)을 우선 건설하여 생산력을 높이는 전략입니다.",
                    "era": "고전/중세",
                    "recommended_items": ["mill", "workshop", "forge"]
                }
            ]
            
            for strategy in production_strategies:
                content = f"""
                전략 이름: {strategy['name']}
                시대: {strategy['era']}
                설명: {strategy['description']}
                추천 생산 항목: {', '.join(strategy['recommended_items'])}
                """
                documents.append(Document(
                    page_content=content,
                    metadata={"type": "strategy", "name": strategy["name"]}
                ))
            
            # FAISS 벡터 스토어 생성
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
            
            # 디렉토리 생성 및 저장
            os.makedirs(self.index_path, exist_ok=True)
            self.vector_store.save_local(self.index_path)
            logger.info(f"FAISS 인덱스를 생성하고 저장했습니다: {self.index_path}")
        
        except Exception as e:
            logger.error(f"벡터 스토어 생성 중 오류 발생: {str(e)}")
    
    def _run(self, query: str) -> str:
        """검색 실행"""
        try:
            if self.vector_store is None:
                self._initialize_vector_store()
            
            # 관련 문서 검색
            docs = self.vector_store.similarity_search(query, k=3)
            
            # 결과 포맷팅
            results = []
            for doc in docs:
                results.append({
                    "content": doc.page_content.strip(),
                    "metadata": doc.metadata
                })
            
            return json.dumps(results, ensure_ascii=False)
        
        except Exception as e:
            logger.error(f"벡터 검색 중 오류 발생: {str(e)}")
            return json.dumps({"error": str(e)})
    
    def _load_unit_data(self) -> List[Dict[str, Any]]:
        """유닛 데이터 로드 (예시)"""
        return [
            {
                "id": "warrior",
                "name": "전사",
                "category": "근접",
                "era": "고대",
                "productionCost": 40,
                "combat_strength": 20,
                "move": 2,
                "description": "기본 근접 전투 유닛"
            },
            {
                "id": "archer",
                "name": "궁수",
                "category": "원거리",
                "era": "고대",
                "productionCost": 40,
                "combat_strength": 15,
                "move": 2,
                "description": "기본 원거리 전투 유닛"
            },
            {
                "id": "settler",
                "name": "개척자",
                "category": "민간",
                "era": "고대",
                "productionCost": 80,
                "move": 2,
                "description": "새로운 도시 건설 가능"
            },
            {
                "id": "builder",
                "name": "건설자",
                "category": "민간",
                "era": "고대",
                "productionCost": 50,
                "move": 2,
                "description": "타일 개선 가능 (3회)"
            },
            {
                "id": "swordsman",
                "name": "검사",
                "category": "근접",
                "era": "고전",
                "productionCost": 60,
                "combat_strength": 35,
                "move": 2,
                "description": "철을 필요로 하는 강력한 근접 유닛"
            },
            {
                "id": "crossbowman",
                "name": "석궁병",
                "category": "원거리",
                "era": "중세",
                "productionCost": 60,
                "combat_strength": 30,
                "move": 2,
                "description": "강력한 원거리 공격"
            },
            {
                "id": "knight",
                "name": "기사",
                "category": "기병",
                "era": "중세",
                "productionCost": 80,
                "combat_strength": 45,
                "move": 4,
                "description": "빠른 속도의 강력한 기병 유닛"
            },
            {
                "id": "pikeman",
                "name": "창병",
                "category": "근접",
                "era": "중세",
                "productionCost": 60,
                "combat_strength": 25,
                "move": 2,
                "description": "기병에 대항하는 특화 유닛"
            },
            {
                "id": "musketman",
                "name": "머스킷병",
                "category": "총기",
                "era": "르네상스",
                "productionCost": 120,
                "combat_strength": 55,
                "move": 2,
                "description": "화약 무기를 사용하는 강력한 유닛"
            }
        ]
    
    def _load_building_data(self) -> List[Dict[str, Any]]:
        """건물 데이터 로드 (예시)"""
        return [
            {
                "id": "granary",
                "name": "곡물 창고",
                "era": "고대",
                "productionCost": 60,
                "description": "도시 식량 생산량 +2"
            },
            {
                "id": "monument",
                "name": "기념비",
                "era": "고대",
                "productionCost": 60,
                "description": "도시 문화 생산량 +2"
            },
            {
                "id": "library",
                "name": "도서관",
                "era": "고대",
                "productionCost": 80,
                "description": "도시 과학 생산량 +2"
            },
            {
                "id": "barracks",
                "name": "병영",
                "era": "고대",
                "productionCost": 80,
                "description": "군사 유닛 생산 시 경험치 +25%"
            },
            {
                "id": "walls",
                "name": "성벽",
                "era": "고대",
                "productionCost": 100,
                "description": "도시 방어력 +5"
            },
            {
                "id": "market",
                "name": "시장",
                "era": "고전",
                "productionCost": 120,
                "description": "도시 골드 생산량 +3"
            },
            {
                "id": "temple",
                "name": "신전",
                "era": "고전",
                "productionCost": 120,
                "description": "도시 신앙 생산량 +3"
            },
            {
                "id": "university",
                "name": "대학",
                "era": "중세",
                "productionCost": 200,
                "description": "도시 과학 생산량 +4"
            },
            {
                "id": "workshop",
                "name": "작업장",
                "era": "중세",
                "productionCost": 150,
                "description": "도시 생산량 +2"
            },
            {
                "id": "bank",
                "name": "은행",
                "era": "르네상스",
                "productionCost": 220,
                "description": "도시 골드 생산량 +4"
            },
            {
                "id": "factory",
                "name": "공장",
                "era": "산업",
                "productionCost": 300,
                "description": "도시 생산량 +4"
            }
        ]
    
    def _load_technology_data(self) -> List[Dict[str, Any]]:
        """기술 데이터 로드 (예시)"""
        return [
            {
                "id": "agriculture",
                "name": "농업",
                "era": "고대",
                "cost": 20,
                "description": "기본 식량 생산 기술"
            },
            {
                "id": "mining",
                "name": "채광",
                "era": "고대",
                "cost": 20,
                "description": "기본 생산력 기술"
            },
            {
                "id": "pottery",
                "name": "도예",
                "era": "고대",
                "cost": 20,
                "description": "식량 저장 및 최초의 건물"
            },
            {
                "id": "animal_husbandry",
                "name": "목축",
                "era": "고대",
                "cost": 35,
                "description": "말과 가축 자원 이용"
            },
            {
                "id": "archery",
                "name": "궁술",
                "era": "고대",
                "cost": 35,
                "description": "원거리 전투 유닛"
            },
            {
                "id": "bronze_working",
                "name": "청동 가공",
                "era": "고대",
                "cost": 50,
                "description": "강력한 근접 유닛"
            },
            {
                "id": "writing",
                "name": "문자",
                "era": "고대",
                "cost": 50,
                "description": "과학 발전의 기초"
            },
            {
                "id": "iron_working",
                "name": "철기",
                "era": "고전",
                "cost": 80,
                "description": "고급 무기 및 갑옷"
            },
            {
                "id": "mathematics",
                "name": "수학",
                "era": "고전",
                "cost": 80,
                "description": "더 높은 과학 발전"
            },
            {
                "id": "engineering",
                "name": "공학",
                "era": "고전",
                "cost": 100,
                "description": "도시 건설 및 방어 강화"
            }
        ]
    
    def _load_era_data(self) -> List[Dict[str, Any]]:
        """시대 데이터 로드 (예시)"""
        return [
            {
                "id": "ancient",
                "name": "고대",
                "description": "문명의 시작, 기본 유닛과 건물 건설 가능"
            },
            {
                "id": "classical",
                "name": "고전",
                "description": "철기와 향상된 건물, 정부 형태의 발전"
            },
            {
                "id": "medieval",
                "name": "중세",
                "description": "기사와 성, 대학과 같은 고급 건물"
            },
            {
                "id": "renaissance",
                "name": "르네상스",
                "description": "화약 무기와 탐험, 새로운 대륙 발견"
            },
            {
                "id": "industrial",
                "name": "산업",
                "description": "공장과 철도, 증기력 유닛 등장"
            },
            {
                "id": "modern",
                "name": "현대",
                "description": "전기와 비행기, 탱크 등의 현대적 유닛"
            },
            {
                "id": "information",
                "name": "정보",
                "description": "컴퓨터와 인터넷, 우주 탐사"
            }
        ] 