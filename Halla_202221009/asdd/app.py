from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from loader import load_pdf_documents
from rag import build_vector_store, create_embeddings, create_llm, create_rag_chain, format_sources


st.set_page_config(page_title="PDF RAG Chatbot", page_icon="📄", layout="wide")

DEFAULT_SEARCH_K = 4
DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 150


@st.cache_resource(show_spinner=False)
def cached_embeddings():
    return create_embeddings()


@st.cache_resource(show_spinner=False)
def cached_llm():
    return create_llm()


def persist_uploads(uploaded_files) -> list[Path]:
    temp_dir = Path(tempfile.mkdtemp(prefix="pdf_rag_"))
    paths: list[Path] = []

    for uploaded_file in uploaded_files:
        file_path = temp_dir / uploaded_file.name
        file_path.write_bytes(uploaded_file.getbuffer())
        paths.append(file_path)

    return paths


def initialize_state() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("vector_store", None)
    st.session_state.setdefault("document_names", [])


initialize_state()

with st.sidebar:
    st.header("PDF")
    uploaded_files = st.file_uploader(
        "PDF 파일 업로드",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if st.button("문서 인덱싱", type="primary", disabled=not uploaded_files):
        try:
            with st.spinner("PDF를 읽고 FAISS 인덱스를 만드는 중입니다..."):
                pdf_paths = persist_uploads(uploaded_files)
                documents = load_pdf_documents(pdf_paths)
                st.session_state.vector_store = build_vector_store(
                    documents=documents,
                    embeddings=cached_embeddings(),
                    chunk_size=DEFAULT_CHUNK_SIZE,
                    chunk_overlap=DEFAULT_CHUNK_OVERLAP,
                )
                st.session_state.document_names = [path.name for path in pdf_paths]
                st.session_state.messages = []
            st.success("인덱싱이 완료되었습니다.")
        except Exception as exc:
            st.error(f"인덱싱 실패: {exc}")

st.title("PDF RAG 챗봇")

if st.session_state.document_names:
    st.caption("인덱싱된 문서: " + ", ".join(st.session_state.document_names))
else:
    st.caption("PDF를 업로드하고 인덱싱한 뒤 질문하세요.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            st.caption("출처: " + ", ".join(message["sources"]))

question = st.chat_input("문서 내용에 대해 질문하세요")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    if st.session_state.vector_store is None:
        answer = "먼저 PDF를 업로드하고 문서 인덱싱을 실행해주세요."
        st.session_state.messages.append({"role": "assistant", "content": answer, "sources": []})
        with st.chat_message("assistant"):
            st.markdown(answer)
    else:
        with st.chat_message("assistant"):
            try:
                with st.spinner("문서 근거를 검색하고 답변을 생성하는 중입니다..."):
                    llm = cached_llm()
                    chain = create_rag_chain(
                        st.session_state.vector_store,
                        llm,
                        search_k=DEFAULT_SEARCH_K,
                    )
                    result = chain.invoke({"input": question})
                    answer = result.get("answer", "").strip() or "문서에서 관련 근거를 찾을 수 없습니다."
                    sources = format_sources(result.get("context", []))

                st.markdown(answer)
                if sources:
                    st.caption("출처: " + ", ".join(sources))
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "sources": sources}
                )
            except Exception as exc:
                error_message = f"답변 생성 실패: {exc}"
                st.error(error_message)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_message, "sources": []}
                )
