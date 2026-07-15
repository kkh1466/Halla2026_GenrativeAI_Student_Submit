from pathlib import Path

from langchain.prompts import PromptTemplate
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

from pdf_loader import load_pdfs, split_documents


CHROMA_DB_DIR = Path("chroma_db")
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 4


RAG_PROMPT_TEMPLATE = """
당신은 PDF 문서를 바탕으로 답변하는 친절한 AI assistant입니다.

아래 Context에 있는 내용만 사용해서 질문에 답변하세요.
Context에서 답을 찾을 수 없다면 모른다고 답변하세요.
답변은 한국어로 작성하고, 초보자도 이해하기 쉽게 설명하세요.

Context:
{context}

Question:
{question}

Answer:
"""


def get_embedding_model():
    """sentence-transformers 기반 임베딩 모델을 생성합니다."""
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)


def is_vector_db_ready():
    """로컬 Chroma 벡터 DB가 존재하는지 확인합니다."""
    return CHROMA_DB_DIR.exists() and any(CHROMA_DB_DIR.iterdir())


def build_vector_db(pdf_paths):
    """PDF를 읽고 chunk로 나눈 뒤 Chroma 벡터 DB에 저장합니다."""
    documents = load_pdfs(pdf_paths)
    split_docs = split_documents(documents, chunk_size=1000, chunk_overlap=200)

    if not split_docs:
        raise ValueError("벡터 DB에 저장할 문서 chunk가 없습니다.")

    embedding_model = get_embedding_model()

    vector_db = Chroma.from_documents(
        documents=split_docs,
        embedding=embedding_model,
        persist_directory=str(CHROMA_DB_DIR),
    )

    return vector_db


def load_vector_db():
    """저장된 Chroma 벡터 DB를 불러옵니다."""
    if not is_vector_db_ready():
        raise FileNotFoundError("벡터 DB가 없습니다. 먼저 벡터 DB를 생성해 주세요.")

    return Chroma(
        persist_directory=str(CHROMA_DB_DIR),
        embedding_function=get_embedding_model(),
    )


def search_relevant_documents(question, top_k=TOP_K):
    """질문과 관련 있는 문서 chunk를 Top-K개 검색합니다."""
    vector_db = load_vector_db()
    return vector_db.similarity_search_with_score(question, k=top_k)


def format_context(search_results):
    """검색된 문서 chunk들을 LLM에 전달할 Context 문자열로 변환합니다."""
    context_parts = []

    for document, score in search_results:
        source = document.metadata.get("source", "알 수 없는 PDF")
        page = document.metadata.get("page", "알 수 없는 페이지")

        context_parts.append(
            f"[파일명: {source}, 페이지: {page}, 검색 점수: {score:.4f}]\n"
            f"{document.page_content}"
        )

    return "\n\n---\n\n".join(context_parts)


def format_sources(search_results, preview_length=300):
    """화면에 표시할 참고 문서명, chunk 일부, 검색 점수를 정리합니다."""
    sources = []

    for document, score in search_results:
        content = document.page_content.replace("\n", " ")
        content_preview = content[:preview_length]

        if len(content) > preview_length:
            content_preview += "..."

        sources.append(
            {
                "file_name": document.metadata.get("source", "알 수 없는 PDF"),
                "page": document.metadata.get("page", "알 수 없는 페이지"),
                "score": float(score),
                "content_preview": content_preview,
            }
        )

    return sources


def get_llm():
    """OpenAI Chat 모델을 생성합니다. 다른 LLM으로 교체할 때 이 함수만 바꾸면 됩니다."""
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


def get_answer_from_question(question):
    """질문을 검색하고, 검색된 Context를 LLM에 전달하여 답변을 생성합니다."""
    search_results = search_relevant_documents(question, top_k=TOP_K)

    if not search_results:
        return "검색된 문서가 없어 답변할 수 없습니다.", []

    context = format_context(search_results)
    sources = format_sources(search_results)

    prompt = PromptTemplate(
        template=RAG_PROMPT_TEMPLATE,
        input_variables=["context", "question"],
    )

    llm = get_llm()
    chain = prompt | llm
    response = chain.invoke({"context": context, "question": question})

    return response.content, sources
