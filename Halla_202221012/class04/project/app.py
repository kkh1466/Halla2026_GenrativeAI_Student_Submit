import os
import shutil
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from pdf_loader import save_uploaded_pdfs
from rag import (
    CHROMA_DB_DIR,
    build_vector_db,
    get_answer_from_question,
    is_vector_db_ready,
)


# .env 파일에 저장된 GOOGLE_API_KEY를 환경 변수로 불러옵니다.
load_dotenv()
st.write("API Key:", os.getenv("GOOGLE_API_KEY"))

DATA_DIR = Path("data")


def initialize_session_state():
    """Streamlit Session State에 필요한 기본값을 준비합니다."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "uploaded_pdf_names" not in st.session_state:
        st.session_state.uploaded_pdf_names = []


def show_chat_history():
    """이전 질문과 답변을 채팅 UI에 다시 표시합니다."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message["role"] == "assistant" and message.get("sources"):
                show_sources(message["sources"])


def show_sources(sources):
    """답변 생성에 참고한 문서와 chunk 내용을 화면에 표시합니다."""
    with st.expander("참고 문서와 검색 점수 보기"):
        for index, source in enumerate(sources, start=1):
            st.markdown(f"**{index}. {source['file_name']}**")
            st.markdown(f"- 검색 점수: `{source['score']:.4f}`")
            st.caption(source["content_preview"])


def delete_vector_db():
    """로컬에 저장된 Chroma 벡터 DB 폴더를 삭제합니다."""
    if CHROMA_DB_DIR.exists():
        shutil.rmtree(CHROMA_DB_DIR)


def render_sidebar():
    """PDF 업로드, 벡터 DB 생성/삭제 버튼을 포함한 사이드바를 그립니다."""
    st.sidebar.header("PDF 문서")

    uploaded_files = st.sidebar.file_uploader(
        "PDF 업로드",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        st.session_state.uploaded_pdf_names = [file.name for file in uploaded_files]

    if st.session_state.uploaded_pdf_names:
        st.sidebar.subheader("업로드한 PDF")
        for file_name in st.session_state.uploaded_pdf_names:
            st.sidebar.write(f"- {file_name}")
    else:
        st.sidebar.info("아직 업로드한 PDF가 없습니다.")

    if st.sidebar.button("벡터 DB 생성", use_container_width=True):
        if not uploaded_files:
            st.sidebar.error("먼저 PDF 파일을 업로드해 주세요.")
            return

        try:
            DATA_DIR.mkdir(exist_ok=True)
            saved_pdf_paths = save_uploaded_pdfs(uploaded_files, DATA_DIR)

            with st.sidebar.status("PDF를 읽고 벡터 DB를 만드는 중입니다...", expanded=True):
                build_vector_db(saved_pdf_paths)

            st.sidebar.success("벡터 DB 생성이 완료되었습니다.")

        except Exception as error:
            st.sidebar.error(f"PDF 처리 중 오류가 발생했습니다: {error}")

    if st.sidebar.button("벡터 DB 삭제", use_container_width=True):
        delete_vector_db()
        st.sidebar.success("벡터 DB를 삭제했습니다.")

    if is_vector_db_ready():
        st.sidebar.success("현재 벡터 DB를 사용할 수 있습니다.")
    else:
        st.sidebar.warning("아직 사용할 수 있는 벡터 DB가 없습니다.")


def handle_user_question(question):
    """사용자 질문을 받아 RAG 답변을 생성하고 채팅 기록에 저장합니다."""
    if not question.strip():
        st.warning("질문을 입력해 주세요.")
        return

    if not is_vector_db_ready():
        st.error("벡터 DB가 없습니다. PDF를 업로드한 뒤 벡터 DB를 먼저 생성해 주세요.")
        return

    if not os.getenv("GOOGLE_API_KEY"):
        st.error("GOOGLE_API_KEY가 없습니다. .env 파일에 API Key를 설정해 주세요.")
        return

    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("답변을 생성하는 중입니다..."):
            try:
                answer, sources = get_answer_from_question(question)
                st.markdown(answer)
                show_sources(sources)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    }
                )

            except Exception as error:
                st.error(f"답변 생성 중 오류가 발생했습니다: {error}")


def main():
    """Streamlit 앱의 시작점입니다."""
    st.set_page_config(page_title="PDF RAG 챗봇", page_icon="📄", layout="wide")

    initialize_session_state()

    st.title("PDF 기반 RAG 챗봇")
    st.caption("PDF 문서를 업로드하고, 문서 내용에 기반해 질문해 보세요.")

    render_sidebar()
    show_chat_history()

    user_question = st.chat_input("PDF 내용에 대해 질문해 보세요.")
    if user_question is not None:
        handle_user_question(user_question)


if __name__ == "__main__":
    main()
