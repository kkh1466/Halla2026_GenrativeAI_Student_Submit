import streamlit as st
import os
from rag import create_vector_db

st.title("📄 PDF RAG")

uploaded_file = st.file_uploader(
    "PDF를 업로드하세요",
    type="pdf"
)

if uploaded_file:

    os.makedirs("uploaded_files", exist_ok=True)

    pdf_path = os.path.join(
        "uploaded_files",
        uploaded_file.name
    )

    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("PDF 저장 완료!")

    db = create_vector_db(pdf_path)

    st.success("벡터 DB 생성 완료!")