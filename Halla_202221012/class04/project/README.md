# PDF 기반 RAG 챗봇

Python, Streamlit, LangChain, ChromaDB를 사용해 만든 PDF 기반 RAG(Retrieval-Augmented Generation) 챗봇입니다.

PDF 파일을 업로드하면 문서 내용을 작은 chunk로 나누고, `sentence-transformers/all-MiniLM-L6-v2` 임베딩 모델로 벡터화한 뒤 ChromaDB에 저장합니다. 사용자가 질문하면 관련 문서 chunk 4개를 검색하고, 검색된 Context를 OpenAI LLM에 전달해 답변을 생성합니다.

## 주요 기능

- 여러 PDF 파일 업로드
- 업로드한 PDF 목록 표시
- 로컬 ChromaDB 벡터 DB 생성 및 삭제
- Streamlit Chat UI
- 이전 질문과 답변 유지
- 답변 생성 중 로딩 표시
- 참고한 PDF 파일명, 관련 chunk 일부, 검색 점수 표시
- 검색된 문서가 없으면 모른다고 답변하도록 Prompt Template 구성
- PDF 미업로드, 벡터 DB 없음, 빈 질문, PDF 읽기 실패, API Key 없음 예외 처리

## 프로젝트 구조

```text
project/
├── app.py              # Streamlit 화면과 사용자 입력 처리
├── rag.py              # 임베딩, ChromaDB, 검색, LLM 답변 생성
├── pdf_loader.py       # PDF 저장, 텍스트 추출, 문서 chunk 분할
├── requirements.txt    # 필요한 Python 패키지 목록
├── .env.example        # 환경 변수 예시 파일
├── README.md           # 프로젝트 설명 문서
└── data/               # 업로드한 PDF가 저장되는 폴더
```

앱 실행 후 벡터 DB를 만들면 `chroma_db/` 폴더가 자동으로 생성됩니다. 이 폴더는 로컬에 유지되므로 프로그램을 껐다 켜도 기존 벡터 DB를 다시 사용할 수 있습니다.

## 설치 방법

Python 3.11 이상을 권장합니다.

```bash
cd project
python -m venv .venv
```

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

macOS 또는 Linux:

```bash
source .venv/bin/activate
```

필요한 라이브러리를 설치합니다.

```bash
pip install -r requirements.txt
```

## API Key 설정 방법

`.env.example` 파일을 복사해 `.env` 파일을 만듭니다.

```bash
copy .env.example .env
```

macOS 또는 Linux에서는 다음 명령을 사용합니다.

```bash
cp .env.example .env
```

`.env` 파일을 열고 OpenAI API Key를 입력합니다.

```env
OPENAI_API_KEY=your_openai_api_key_here
```

## 실행 방법

```bash
streamlit run app.py
```

브라우저가 열리면 다음 순서로 사용합니다.

1. 왼쪽 사이드바에서 PDF 파일을 업로드합니다.
2. `벡터 DB 생성` 버튼을 누릅니다.
3. 메인 화면의 채팅 입력창에 질문을 입력합니다.
4. 답변 아래의 `참고 문서와 검색 점수 보기`를 열어 어떤 문서를 참고했는지 확인합니다.

## 사용 라이브러리

- `streamlit`: 웹 UI와 Chat UI 구성
- `langchain`: RAG 파이프라인, Prompt Template, Text Splitter
- `langchain-chroma`: ChromaDB 연동
- `langchain-huggingface`: HuggingFace 임베딩 모델 연동
- `langchain-openai`: OpenAI Chat 모델 연동
- `chromadb`: 로컬 벡터 DB
- `sentence-transformers`: `all-MiniLM-L6-v2` 임베딩 모델 사용
- `pypdf`: PDF 텍스트 추출
- `python-dotenv`: `.env` 환경 변수 로드
- `openai`: OpenAI API 사용

## LLM 교체 방법

LLM을 다른 모델로 바꾸고 싶다면 `rag.py`의 `get_llm()` 함수만 수정하면 됩니다.

```python
def get_llm():
    """OpenAI Chat 모델을 생성합니다. 다른 LLM으로 교체할 때 이 함수만 바꾸면 됩니다."""
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)
```

예를 들어 로컬 LLM이나 다른 API 모델을 사용하려면 이 함수에서 LangChain이 지원하는 다른 Chat Model 객체를 반환하도록 변경하면 됩니다.

## 참고 사항

- 스캔본 PDF처럼 텍스트가 이미지로 들어 있는 문서는 `pypdf`만으로 텍스트 추출이 어려울 수 있습니다.
- ChromaDB 검색 점수는 값이 낮을수록 더 가까운 문서로 해석되는 경우가 많습니다.
- 처음 임베딩 모델을 사용할 때 모델 파일 다운로드가 필요해 시간이 걸릴 수 있습니다.
