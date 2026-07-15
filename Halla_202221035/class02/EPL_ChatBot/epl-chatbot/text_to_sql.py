
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
 
# 한글 팀 별명 -> 실제 DB 저장명(영문) 매핑
TEAM_NAME_MAP = """
한글 팀 별명 -> 실제 DB 저장명 매핑 (질문에 한글 팀명이 나오면 아래를 참고해
영어 팀명으로 변환한 뒤 LIKE 검색에 사용하세요):
- 맨시티, 맨체스터시티 -> Manchester City
- 맨유, 맨체스터유나이티드 -> Manchester United
- 아스날 -> Arsenal
- 첼시 -> Chelsea
- 리버풀 -> Liverpool
- 토트넘, 스퍼스 -> Tottenham
- 뉴캐슬 -> Newcastle
- 브라이튼 -> Brighton
- 웨스트햄 -> West Ham
- 에버튼 -> Everton
- 울버햄튼, 울브스 -> Wolverhampton
- 크리스탈팰리스 -> Crystal Palace
- 풀럼 -> Fulham
- 브렌트포드 -> Brentford
- 노팅엄포레스트 -> Nottingham Forest
- 애스턴빌라 -> Aston Villa
- 본머스 -> Bournemouth
- 손흥민 -> Son Heung-min (DB에 다른 표기로 저장됐을 수 있으니 '%Son%'처럼 성만으로도 검색)
"""
 
SYSTEM_PROMPT = f"""당신은 SQLite 전문가입니다. 사용자의 한글 질문을 아래 스키마에 맞는
SQLite SELECT 쿼리로만 변환하세요.
 
{SCHEMA_DESCRIPTION}
 
{TEAM_NAME_MAP}
 
규칙:
- 오직 SQL 쿼리만 출력하세요. 설명, 마크다운 코드블록(```), 그 어떤 부가 텍스트도 넣지 마세요.
- SELECT 문만 작성하세요 (INSERT/UPDATE/DELETE/DROP 금지).
- 팀 이름/선수 이름은 LIKE '%이름%' 형태로 부분 일치 검색을 사용하세요 (표기 차이 대응).
- 선수 이름은 확실하지 않으면 성(last name)만으로 LIKE 검색하세요 (예: '손흥민' -> '%Son%').
- 득점 시간을 묻는 질문은 반드시 match_events.minute을 사용하세요.
- "누가 골을 많이 넣었는지", "득점 순위" 같은 랭킹/집계 질문은 반드시 GROUP BY와 COUNT(*)를 사용하고,
  결과 컬럼 별칭은 goal_count 처럼 명확하게 지정하고, ORDER BY goal_count DESC로 정렬하세요.
  예: SELECT player, COUNT(*) as goal_count FROM match_events WHERE event_type='goal'
      GROUP BY player ORDER BY goal_count DESC LIMIT 10
- 결과가 많을 수 있는 질문은 LIMIT 20을 기본으로 붙이세요.
- 이전 대화(직전에 생성된 SQL 포함)가 함께 주어질 경우, 이번 질문이 "그럼", "거기서", "어떤 경기에서" 처럼
  이전 질문의 대상(선수/팀 등)을 이어받는 후속 질문인지 반드시 판단하세요.
  후속 질문이라면 이전 SQL에서 사용된 WHERE 조건(예: player LIKE '%Son%')을 이번 SQL에도 동일하게 유지하세요.
  이전 맥락과 무관하게 완전히 새로운 주제의 질문이면 새 조건으로 작성하세요.
"""
 
# 히스토리에 보관할 최근 대화 턴 수 (user+assistant 합쳐서 이 개수 x 2 만큼 유지)
MAX_HISTORY_TURNS = 3
 
 
def question_to_sql(question: str, history: list[dict] | None = None) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        # 너무 길어지는 것을 방지하기 위해 최근 N턴만 사용
        messages.extend(history[-MAX_HISTORY_TURNS * 2:])
    messages.append({"role": "user", "content": question})
 
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
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
 
 
def answer_question(question: str, history: list[dict] | None = None) -> dict:
    """전체 파이프라인: 질문 -> SQL -> 실행 -> 자연어 요약
 
    history: [{"role": "user"/"assistant", "content": ...}, ...] 형태로,
             이전 질문(user)과 그에 대해 생성된 SQL(assistant)을 번갈아 담아서 전달하면
             후속 질문(예: "어떤 경기에서 제일 많이 넣었어?")의 맥락을 GPT가 이어받을 수 있습니다.
    """
    sql = question_to_sql(question, history)
    try:
        columns, rows = run_sql(sql)
        answer = summarize_result(question, columns, rows)
        return {"sql": sql, "columns": columns, "rows": rows, "answer": answer, "error": None}
    except Exception as e:
        return {"sql": sql, "columns": [], "rows": [], "answer": None, "error": str(e)}