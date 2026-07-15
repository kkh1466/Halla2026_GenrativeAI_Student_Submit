# ✈️ RAG 기반 AI 여행 · 데이트 코스 추천 시스템

> FastAPI + Streamlit + OpenAI + ChromaDB를 활용한 RAG 기반 여행/데이트
> 코스 추천 서비스

## 📖 프로젝트 소개

이 프로젝트는 사용자의 여행 또는 데이트 요청을 분석하여 직접 수집한 장소
데이터를 기반으로 하루 코스를 추천하는 AI 서비스입니다.

일반 GPT처럼 학습된 지식만 사용하는 것이 아니라, 직접 크롤링한 데이터를
ChromaDB에 저장하고 RAG(Retrieval-Augmented Generation)를 이용해 검색한
후 GPT-4o-mini가 추천 코스를 생성합니다.

------------------------------------------------------------------------

## ✨ 주요 기능

-   장소 데이터 크롤링 및 JSON 저장
-   OpenAI Embedding을 이용한 벡터 생성
-   ChromaDB를 이용한 의미 기반 검색(RAG)
-   GPT-4o-mini를 이용한 여행/데이트 코스 생성
-   이동 순서 및 추천 이유 제공
-   Streamlit 기반 사용자 인터페이스

------------------------------------------------------------------------

## 🛠 기술 스택

  분야          기술
  ------------- ------------------------
  Language      Python
  Backend       FastAPI
  Frontend      Streamlit
  AI Model      GPT-4o-mini
  Embedding     text-embedding-3-small
  Vector DB     ChromaDB
  Crawling      Crawl4AI
  Data          JSON
  Environment   python-dotenv

------------------------------------------------------------------------

## 🏗 시스템 구조

``` text
사용자
   │
   ▼
Streamlit
   │
   ▼
FastAPI
   │
   ▼
OpenAI Embedding
   │
   ▼
ChromaDB
(RAG Retrieval)
   │
   ▼
GPT-4o-mini
(Generation)
   │
   ▼
데이트/여행 코스 생성
```

------------------------------------------------------------------------

## 📂 프로젝트 구조

``` text
TravelAi/
│
├── app.py
├── streamlit_app.py
├── pipeline.py
├── crawl_data.json
├── chroma_db/
├── .env
├── requirements.txt
└── README.md
```

------------------------------------------------------------------------

## 🔄 RAG 동작 과정

1.  Crawl4AI로 여행 장소 데이터 수집
2.  JSON 파일 생성
3.  `pipeline.py`에서 Embedding 생성
4.  ChromaDB에 벡터 저장
5.  사용자가 질문 입력
6.  질문을 Embedding으로 변환
7.  ChromaDB에서 관련 장소 검색(Retrieval)
8.  검색 결과를 GPT-4o-mini에 전달
9.  GPT가 하루 코스 생성(Generation)

------------------------------------------------------------------------

## 🚀 실행 방법

### 1. 저장소 Clone

``` bash
git clone https://github.com/<YOUR_GITHUB_ID>/<YOUR_REPOSITORY>.git
cd <YOUR_REPOSITORY>
```

### 2. 가상환경 생성

``` bash
python -m venv .venv
```

Windows

``` bash
.\.venv\Scripts\activate
```

### 3. 라이브러리 설치

``` bash
pip install -r requirements.txt
```

### 4. OpenAI API Key 설정

프로젝트 루트에 `.env` 파일 생성

``` env
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
```

### 5. ChromaDB 생성

``` bash
python pipeline.py
```

### 6. FastAPI 실행

``` bash
uvicorn app:app --reload
```

### 7. Streamlit 실행

``` bash
streamlit run streamlit_app.py
```

------------------------------------------------------------------------

## 📡 API

### GET /

서버 실행 확인

### POST /add

장소 데이터를 ChromaDB에 저장

### POST /chat

사용자 질문을 기반으로 RAG 검색 후 여행 코스를 생성

------------------------------------------------------------------------

## 📸 실행 화면

> Streamlit 실행 화면 및 추천 결과 스크린샷을 추가하면 좋습니다.

------------------------------------------------------------------------

## 🚀 향후 개선

-   Kakao Map API 연동
-   Google Maps API 연동
-   실제 이동시간 계산
-   지도 기반 동선 시각화
-   실시간 영업 정보 반영
-   사용자 현재 위치 기반 추천

------------------------------------------------------------------------

## 👨‍💻 Team

-   최해준
-   김형민
-   이채은

------------------------------------------------------------------------

본 프로젝트는 OpenAI API와 RAG(Retrieval-Augmented Generation)를
활용하여 실제 장소 데이터를 기반으로 여행 및 데이트 코스를 추천하는 AI
시스템입니다.
