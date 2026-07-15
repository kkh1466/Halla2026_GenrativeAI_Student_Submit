"""
OpenAI GPT를 이용해 한글 자연어 질문을 SQLite 쿼리로 변환하고,
실행 결과를 다시 자연어로 요약하는 모듈.
"""
import os
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv
from database.db_utils import get_connection

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# GPT에게 알려줄 DB 스키마 설명 (질문 -> SQL 변환 정확도의 핵심)
SCHEMA_DESCRIPTION = """
테이블 1: matches (경기 기본 정보)
- match_id (TEXT, PK)
- season (TEXT, 예: "2024-2025")
- date (TEXT, YYYY-MM-DD)
- home_team (TEXT)
- away_team (TEXT)
- home_score (INTEGER)
- away_score (INTEGER)

테이블 2: match_events (경기 내 이벤트: 골, 카드 등)
- match_id (TEXT, matches.match_id 참조)
- minute (INTEGER, 이벤트 발생 시간)
- team (TEXT, 이벤트를 일으킨 팀)
- event_type (TEXT, 'goal' / 'own_goal' / 'yellow_card' / 'red_card')
- player (TEXT, 득점자/해당 선수)
- assist_player (TEXT, 어시스트 선수, 없으면 NULL)
- xg (REAL, 기대득점, Understat 데이터에만 존재)

두 테이블은 match_id로 JOIN 가능.
"""

SYSTEM_PROMPT = f"""당신은 SQLite 전문가입니다. 사용자의 한글 질문을 아래 스키마에 맞는
SQLite SELECT 쿼리로만 변환하세요.

{SCHEMA_DESCRIPTION}

규칙:
- 오직 SQL 쿼리만 출력하세요. 설명, 마크다운 코드블록(```), 그 어떤 부가 텍스트도 넣지 마세요.
- SELECT 문만 작성하세요 (INSERT/UPDATE/DELETE/DROP 금지).
- 팀 이름/선수 이름은 LIKE '%이름%' 형태로 부분 일치 검색을 사용하세요 (표기 차이 대응).
- 득점 시간을 묻는 질문은 반드시 match_events.minute을 사용하세요.
- 결과가 많을 수 있는 질문은 LIMIT 20을 기본으로 붙이세요.
"""


def question_to_sql(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    sql = response.choices[0].message.content.strip()
    # 혹시 모를 마크다운 코드블록 제거
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


def run_sql(sql: str) -> tuple[list, list]:
    """생성된 SQL을 실행합니다. SELECT 문이 아니면 차단합니다."""
    if not sql.strip().lower().startswith("select"):
        raise ValueError("안전을 위해 SELECT 쿼리만 실행할 수 있습니다.")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql)
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    return columns, rows


def summarize_result(question: str, columns: list, rows: list) -> str:
    """조회 결과를 자연스러운 한글 문장으로 요약합니다."""
    if not rows:
        return "조회 결과가 없습니다. 질문을 다르게 표현해보시겠어요?"

    data_preview = "\n".join(
        ", ".join(f"{col}: {val}" for col, val in zip(columns, row)) for row in rows[:20]
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "당신은 축구 데이터 분석가입니다. 아래 SQL 조회 결과를 바탕으로 "
                "사용자 질문에 자연스러운 한글로 답변하세요. 데이터에 없는 내용은 지어내지 마세요.",
            },
            {
                "role": "user",
                "content": f"질문: {question}\n\n조회 결과:\n{data_preview}",
            },
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def answer_question(question: str) -> dict:
    """전체 파이프라인: 질문 -> SQL -> 실행 -> 자연어 요약"""
    sql = question_to_sql(question)
    try:
        columns, rows = run_sql(sql)
        answer = summarize_result(question, columns, rows)
        return {"sql": sql, "columns": columns, "rows": rows, "answer": answer, "error": None}
    except Exception as e:
        return {"sql": sql, "columns": [], "rows": [], "answer": None, "error": str(e)}
