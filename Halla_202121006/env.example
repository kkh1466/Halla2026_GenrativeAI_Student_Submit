# ⚽ EPL 데이터 챗봇

프리미어리그 경기 결과, 득점자, 어시스트, 득점 시간을 한글 자연어로 질문하면
GPT가 SQL로 변환해 SQLite DB에서 조회하고 답변해주는 챗봇입니다.

## 폴더 구조
```
epl-chatbot/
├── app.py                          # Streamlit 챗봇 UI (진입점)
├── text_to_sql.py                  # 질문 → SQL 변환 + 결과 요약 (OpenAI)
├── requirements.txt
├── .env.example                    # API 키 설정 예시
├── database/
│   ├── schema.sql                  # matches / match_events 테이블 정의
│   └── db_utils.py                 # DB 연결/초기화
└── data_collection/
    ├── collect_understat.py        # 득점자/시간/xG 수집 (무료)
    └── collect_api_football.py     # 어시스트/카드 등 보완 수집 (하루 100회 무료)
```

## 시작하기 (VSCode)

### 1. 가상환경 생성 및 패키지 설치
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

### 2. API 키 설정
`.env.example`을 복사해 `.env` 파일을 만들고 실제 키를 채워넣으세요.
```bash
cp .env.example .env
```
- `OPENAI_API_KEY`: OpenAI 대시보드에서 발급
- `RAPIDAPI_KEY`: RapidAPI에서 API-Football 구독 후 발급 (무료 플랜)

### 3. 데이터 수집
```bash
# 1) Understat에서 득점자/시간/xG 수집 (먼저 실행)
python data_collection/collect_understat.py

# 2) API-Football에서 어시스트/카드 등 보완 수집 (하루 100회 제한, 여러 날 나눠 실행 가능)
python data_collection/collect_api_football.py
```
같은 스크립트를 다음날 다시 실행하면 이미 수집한 경기는 건너뛰고 이어서 수집합니다.

### 4. 챗봇 실행
```bash
streamlit run app.py
```
브라우저가 자동으로 열리며 `http://localhost:8501`에서 챗봇을 사용할 수 있습니다.

## 사용 예시 질문
- "2024-25 시즌 맨체스터 시티와 아스날 경기 결과 알려줘"
- "손흥민이 이번 시즌 몇 분에 골을 가장 많이 넣었어?"
- "홀란드 어시스트한 선수 누구야?"

## 알려진 제약사항
- Understat 데이터의 팀/선수 이름 표기가 API-Football과 다를 수 있어, 정확한 매칭을 위해
  나중에 팀명 통일 매핑 테이블을 추가하는 게 좋습니다 (soccerdata의 teamname_replacements 참고).
- `soccerdata`의 `read_shot_events()` 등 실제 컬럼명은 라이브러리 버전에 따라 다를 수 있으니,
  최초 실행 시 콘솔에 출력되는 컬럼 목록을 확인하고 필요하면 코드의 컬럼명을 맞춰주세요.
- GPT가 생성한 SQL은 100% 정확하지 않을 수 있어 "생성된 SQL 보기"로 항상 검증 가능하게 만들었습니다.
