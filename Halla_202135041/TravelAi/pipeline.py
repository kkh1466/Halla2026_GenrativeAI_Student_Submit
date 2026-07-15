import json
import os
import uuid

import chromadb
from openai import OpenAI
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chroma_db")

chroma_client = chromadb.PersistentClient(path=DB_PATH)

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==========================
# Chroma DB
# ==========================

chroma_client = chromadb.PersistentClient(path="./chroma_db")

collection = chroma_client.get_or_create_collection(
    name="travel_data"
)

# 기존 DB 비우기 (새로 구축)
try:
    collection.delete(where={})
except:
    pass

# ==========================
# JSON 읽기
# ==========================

with open("crawl_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# ==========================
# 리스트 평탄화
# ==========================

places = []


def flatten(item):
    if isinstance(item, dict):
        places.append(item)
    elif isinstance(item, list):
        for x in item:
            flatten(x)


flatten(data)

print(f"총 장소 개수 : {len(places)}")

saved = 0
saved_places = set()

# 버릴 이름들
ignore_names = {
    "",
    "N/A",
    "해당 정보 없음",
    "정보 없음",
    "네이버 블로그",
    "네이버 여행 서비스",
    "네이버 백신",
    "악성코드 포함 파일",
    "악성코드가 포함되어 있는 파일입니다.",
    "안부글 작성 제한",
    "저작권 침해 우려 컨텐츠"
}

# ==========================
# 저장
# ==========================

for place in places:

    if place.get("error", False):
        continue

    place_name = str(place.get("place_name", "")).strip()
    category = str(place.get("category", "")).strip()
    location = str(place.get("location", "")).strip()
    cost = str(place.get("estimated_cost", "")).strip()
    hours = str(place.get("business_hours", "")).strip()
    parking = str(place.get("parking_info", "")).strip()
    weather = str(place.get("recommended_weather", "")).strip()
    summary = str(place.get("review_summary", "")).strip()

    tags = place.get("atmosphere_tags", [])

    if isinstance(tags, list):
        tags = ", ".join(tags)
    else:
        tags = str(tags)

    # ------------------------
    # 이상한 데이터 제거
    # ------------------------

    if place_name in ignore_names:
        continue

    if len(place_name) <= 1:
        continue

    if "네이버" in place_name:
        continue

    if "악성코드" in place_name:
        continue

    if "안부글" in place_name:
        continue

    if "저작권" in place_name:
        continue

    # ------------------------
    # 중복 제거
    # ------------------------

    key = (
        place_name.lower().replace(" ", ""),
        location.lower().replace(" ", "")
    )

    if key in saved_places:
        continue

    saved_places.add(key)

    # ------------------------
    # Document 생성
    # ------------------------

    document = f"""
장소명 : {place_name}

카테고리 : {category}

위치 : {location}

예상비용 : {cost}

영업시간 : {hours}

주차 : {parking}

추천날씨 : {weather}

분위기 :
{tags}

리뷰 :
{summary}

이 장소는 데이트 코스에 활용 가능한 장소이다.

같은 지역의 장소들과 함께 하루 코스를 만들 수 있다.

커플 추천.

사진 찍기 좋음.

여행 추천.
"""

    # ------------------------
    # Embedding
    # ------------------------

    embedding = client.embeddings.create(
        model="text-embedding-3-small",
        input=document
    ).data[0].embedding

    # ------------------------
    # 저장
    # ------------------------

    collection.add(
        ids=[str(uuid.uuid4())],
        documents=[document],
        embeddings=[embedding],
        metadatas=[{
            "place_name": place_name,
            "category": category,
            "location": location,
            "weather": weather
        }]
    )

    saved += 1

    print(f"저장 완료 : {place_name}")

print("DB 저장 확인용")
print(collection.count())
print()
print("=" * 50)
print(f"최종 저장 개수 : {saved}")
print("=" * 50)