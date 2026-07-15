import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
# 임베딩과 모델 로딩을 아주 가볍게 변경
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

st.title("⚽ 챔스 전문가 AI 봇 (가벼운 모드)")

@st.cache_resource
def load_data():
    # PDF 로딩
    loader = PyPDFLoader("UCL_Mini-Tech-Report_2026_DIGITAL_v1.pdf")
    chunks = loader.load_and_split()
    # 가장 가벼운 임베딩 모델 사용
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    return vectorstore.as_retriever(search_kwargs={"k": 2})

retriever = load_data()
st.write("✅ 데이터 로딩 완료! 이제 질문하세요.")

if prompt := st.chat_input("질문을 입력하세요"):
    st.write(f"질문: {prompt}")
    docs = retriever.invoke(prompt)
    st.write("검색된 정보:")
    for doc in docs:
        st.write(doc.page_content[:200]) # 답변 대신 검색된 내용만 먼저 띄워보기