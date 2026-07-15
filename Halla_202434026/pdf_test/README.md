# 📄 PDF RAG Chatbot

## 소개

Gemini와 LangChain을 이용한 PDF 기반 RAG 챗봇입니다.

## 사용 기술

- Streamlit
- LangChain
- FAISS
- HuggingFace Embedding
- Gemini API

## 실행 방법

```bash
pip install -r requirements.txt

streamlit run app.py
```

## API Key 설정

```python
os.environ["GOOGLE_API_KEY"] = "YOUR_API_KEY"
```