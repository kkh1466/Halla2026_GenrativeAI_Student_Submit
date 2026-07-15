# Streamlit PDF RAG Chatbot

Streamlit, LangChain, FAISS, Hugging Face Transformers 기반의 로컬 PDF RAG 챗봇입니다. 업로드한 PDF에서 검색된 context만 사용해 한국어로 답변하도록 구성했습니다.

## 요구사항

- Python 3.11
- Windows, macOS, Linux

## 설치 및 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

처음 실행할 때 다음 모델이 자동으로 다운로드됩니다.

- LLM: `google/flan-t5-base`
- Embedding: `sentence-transformers/all-MiniLM-L6-v2`

## 사용 방법

1. 사이드바에서 PDF 파일을 업로드합니다.
2. `문서 인덱싱` 버튼을 눌러 FAISS 인덱스를 생성합니다.
3. 채팅창에서 PDF 내용에 대해 질문합니다.

## 구성

- `app.py`: Streamlit UI와 채팅 흐름
- `rag.py`: Hugging Face Transformers LLM, 임베딩, FAISS, RAG 체인
- `loader.py`: PDF 로딩과 문서 분할
- `prompts.py`: context 기반 한국어 답변 프롬프트
- `requirements.txt`: 의존성

## 구현 메모

- `transformers`의 `AutoTokenizer`, `AutoModelForSeq2SeqLM`, `pipeline`을 사용합니다.
- 기본 LLM은 `google/flan-t5-base`입니다.
- 임베딩 모델은 `sentence-transformers/all-MiniLM-L6-v2`입니다.
- LangChain 0.3.x 계열의 LCEL Runnable 체인으로 retriever, prompt, LLM, output parser를 연결합니다.
- LangChain의 최신 LCEL Runnable 패턴을 사용합니다.
- 검색 결과의 `source`, `page` 메타데이터를 출처로 표시합니다.
