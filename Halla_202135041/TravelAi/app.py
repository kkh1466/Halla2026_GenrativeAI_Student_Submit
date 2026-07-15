from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os
import chromadb
import uuid
 
# =========================
# 기본 설정
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chroma_db")
load_dotenv()
app = FastAPI()
 
# =========================
# OpenAI
# =========================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
# =========================
# ChromaDB (반드시 형민님이 만든 실제 컬렉션 이름으로!)
# =========================
chroma_client = chromadb.PersistentClient(path=DB_PATH)
collection = chroma_client.get_or_create_collection(name="course_places")  # travel_data -> course_places 로 수정
 
# =========================
# 요청 모델
# =========================
class AddRequest(BaseModel):
    text: str
    region: str = "unknown"
    category: str = "general"
 
class ChatRequest(BaseModel):
    question: str
    region: str = "서울"        # 프론트에서 넘겨줄 값. 안 넘어오면 기본값 "서울"
    budget: int = 0             # 1인당 예산(원). 0이면 예산 제한 없음 (선택 입력)
    people: int = 1             # 인원수 (선택 입력, 기본 1명)
 
# =========================
# 기본 API
# =========================
@app.get("/")
def home():
    return {"message": "Travel AI Running"}
 
@app.get("/debug-db")
def debug_db():
    return {
        "count": collection.count()
    }
 
# =========================
# 데이터 추가 API
# =========================
@app.post("/add")
def add_data(req: AddRequest):
    try:
        embedding = client.embeddings.create(
            model="text-embedding-3-small",
            input=req.text
        ).data[0].embedding
        collection.add(
            ids=[str(uuid.uuid4())],
            documents=[req.text],
            embeddings=[embedding],
            metadatas=[{
                "region": req.region,
                "category": req.category,
                "place_name": req.text[:30],
                "location": "unknown"
            }]
        )
        return {"status": "saved"}
    except Exception as e:
        return {"error": str(e)}
 
# =========================
# 슬롯별 후보 검색 (RAG 개선 - hallucination 방지 + 예산/인원 반영)
# =========================
SLOTS = [
    {"name": "카페", "emoji": "☕", "query": "감성 카페 소품샵",   "category_filter": ["카페", "소품샵"]},
    {"name": "관광", "emoji": "🏛️", "query": "관광지 명소",         "category_filter": ["관광지"]},
    {"name": "체험", "emoji": "🎨", "query": "체험 액티비티",       "category_filter": ["체험", "관광지"]},
    {"name": "저녁", "emoji": "🍽️", "query": "저녁 맛집",           "category_filter": ["맛집"]},
    {"name": "야경", "emoji": "🌃", "query": "야경 명소",           "category_filter": ["관광지"]},
]
 
def get_slot_candidates(region: str, slot: dict, people: int, budget: int, top_k: int = 12):
    and_conditions = [
        {"region": region},
        {"category": {"$in": slot["category_filter"]}},
        {"min_people": {"$lte": people}},
        {"max_people": {"$gte": people}},
    ]
    if budget and budget > 0:
        and_conditions.append({"estimated_price_per_person": {"$lte": budget}})
 
    where_filter = {"$and": and_conditions}
    results = collection.query(
        query_texts=[slot["query"]],
        n_results=top_k,
        where=where_filter,
    )
    # 예산 조건 때문에 후보가 0개면 예산 조건만 풀고 재검색 (빈 슬롯 방지)
    if not results.get("documents", [[]])[0] and budget and budget > 0:
        fallback_conditions = and_conditions[:-1]  # 예산 조건 제거
        results = collection.query(
            query_texts=[slot["query"]],
            n_results=top_k,
            where={"$and": fallback_conditions},
        )
    return results
 
def build_candidate_block(slot_name: str, emoji: str, results) -> str:
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    if not docs:
        return f"[{emoji} {slot_name}] 후보 없음 (이 슬롯은 코스에서 제외할 것)"
    lines = [f"[{emoji} {slot_name} 후보 목록]"]
    for meta in metas:
        name = meta.get("name", "이름 없음")
        sub_region = meta.get("sub_region", "정보 없음")
        price = meta.get("estimated_price_per_person", "정보 없음")
        transport = meta.get("access_transport", "정보 없음")
        lines.append(
            f"- {name} | 동네: {sub_region} | 1인 예상 비용: {price}원 | 접근 교통: {transport}"
        )
    return "\n".join(lines)
 
def build_system_prompt(region: str, user_question: str, people: int, budget: int) -> str:
    blocks = []
    for slot in SLOTS:
        combined_slot = {**slot, "query": f"{user_question} {slot['query']}"}
        blocks.append(build_candidate_block(slot["name"], slot["emoji"], get_slot_candidates(region, combined_slot, people, budget)))
    candidate_list = "\n\n".join(blocks)
 
    budget_line = (
        f"- 1인당 총 예산은 약 {budget}원입니다. 코스 전체 합산 비용이 이 예산을 넘지 않도록 구성하라."
        if budget and budget > 0 else
        "- 예산 제한은 특별히 없지만, 각 장소의 예상 비용은 반드시 함께 안내하라."
    )
    people_line = f"- 인원수는 {people}명 기준입니다."
 
    return f"""
너는 대한민국 최고의 데이트 코스 플래너이다. 딱딱한 안내문처럼 쓰지 말고, 친근하고 신나는 톤으로 이모지를 적극 활용해서 작성하라.
 
아래는 시간대(슬롯)별로 미리 검색된 후보 목록이다. 각 후보에는 동네, 1인 예상 비용, 접근 교통 정보가 함께 제공된다.
실제 좌표(위도/경도) 데이터는 없으므로, 정확한 분 단위 이동시간 계산은 불가능하다. 대신 아래 규칙으로 "예상 이동시간"을 근사치로 추정해서 반드시 표시하라.
 
[이동시간 추정 규칙]
- 바로 이전 장소와 같은 동네(sub_region)인 경우 -> "🚶 도보 이동 (약 5~10분)"
- 바로 이전 장소와 다른 동네(sub_region)인 경우 -> "🚕 대중교통/택시 이동 (약 20~30분)"
- 코스의 첫 번째 장소는 "🏁 이동시간 없음(코스 시작)"으로 표시
 
[이모지 사용 규칙 - 반드시 지킬 것]
- 각 슬롯(카페/관광/체험/저녁/야경)에는 아래 이모지를 그 슬롯 이름 앞에 반드시 붙여라: ☕ 카페 / 🏛️ 관광 / 🎨 체험 / 🍽️ 저녁 / 🌃 야경
- 장소 설명(선택 이유)에도 분위기나 상황에 어울리는 이모지를 1~2개씩 자연스럽게 섞어라. (예: 사진 맛집이면 📸, 분위기 좋으면 ✨, 뷰가 좋으면 🌇, 인기 많으면 🔥 등) 단, 매 줄 같은 이모지만 반복하지 말고 상황에 맞게 다양하게 사용하라.
- 예상 비용 앞에는 💰, 예상 이동시간 앞에는 위 이동시간 규칙의 이모지를 사용하라.
- 마지막 총 예상 비용 줄 앞에는 🧾를 붙여라.
 
[출력 규칙 - 반드시 지킬 것]
- 각 슬롯에서는 반드시 그 슬롯의 후보 목록 안에서만 장소를 골라야 한다. 후보에 없는 장소는 절대 만들어내지 마라.
- 후보가 "없음"으로 표시된 슬롯은 코스에서 제외하라.
{budget_line}
{people_line}
- 각 장소는 아래 형식을 반드시 지켜서 출력하라 (이모지 포함):
  "N. [슬롯이모지] 장소명 (동네) - 선택 이유 1문장(상황에 맞는 이모지 포함) | 💰 예상 비용: OOOO원 | 이동시간 이모지 예상 이동시간: OOO"
- 후보 목록의 첫 번째 장소만 기계적으로 고르지 말고, 사용자 질문 의도에 맞게 후보 전체를 고르게 검토하라.
- 코스 마지막 줄에 "🧾 총 예상 비용(1인 기준): 000원"으로 합계를 요약하라.
 
{candidate_list}
 
카페 → 관광 → 체험 → 저녁 → 야경 순으로 구성해라.
"""
 
# =========================
# RAG CHAT
# =========================
def detect_region(question: str, fallback: str = "서울") -> str:
    if "강릉" in question:
        return "강릉"
    if "서울" in question:
        return "서울"
    return fallback
 
@app.post("/chat")
def chat(req: ChatRequest):
    try:
        region = detect_region(req.question, fallback=req.region)
        system_prompt = build_system_prompt(region, req.question, req.people, req.budget)
 
        no_candidates = all(
            f"[{slot['emoji']} {slot['name']}] 후보 없음" in system_prompt for slot in SLOTS
        )
        if no_candidates:
            return {"answer": "😥 조건에 맞는 장소를 찾지 못했어요. 예산이나 인원수를 조정해서 다시 시도해주세요!"}
 
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.6,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.question}
            ]
        )
        return {
            "answer": response.choices[0].message.content
        }
    except Exception as e:
        return {"error": str(e)}