from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
from transformers.pipelines import Pipeline

from loader import split_documents
from prompts import DOCUMENT_PROMPT, QA_PROMPT


EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_LLM_MODEL_NAME = "google/flan-t5-base"


def create_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def create_llm(
    model_name: str = DEFAULT_LLM_MODEL_NAME,
    max_new_tokens: int = 256,
    temperature: float = 0.0,
) -> Pipeline:
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    generation_kwargs: dict[str, Any] = {
        "max_new_tokens": max_new_tokens,
        "do_sample": temperature > 0,
    }
    if temperature > 0:
        generation_kwargs["temperature"] = temperature

    return pipeline(
        task="text2text-generation",
        model=model,
        tokenizer=tokenizer,
        **generation_kwargs,
    )


def build_vector_store(
    documents: list[Document],
    embeddings: HuggingFaceEmbeddings | None = None,
    chunk_size: int = 900,
    chunk_overlap: int = 150,
) -> FAISS:
    if not documents:
        raise ValueError("PDF에서 읽을 수 있는 텍스트를 찾지 못했습니다.")

    chunks = split_documents(
        documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    if not chunks:
        raise ValueError("문서를 청크로 분할하지 못했습니다.")

    return FAISS.from_documents(chunks, embeddings or create_embeddings())


def load_vector_store(index_dir: str | Path, embeddings: HuggingFaceEmbeddings | None = None) -> FAISS:
    return FAISS.load_local(
        str(index_dir),
        embeddings or create_embeddings(),
        allow_dangerous_deserialization=True,
    )


def save_vector_store(vector_store: FAISS, index_dir: str | Path) -> None:
    Path(index_dir).mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(index_dir))


def create_rag_chain(
    vector_store: FAISS,
    llm: Pipeline,
    search_k: int = 4,
) -> Runnable[dict[str, Any], dict[str, Any]]:
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": search_k},
    )

    def retrieve(inputs: dict[str, Any]) -> list[Document]:
        return retriever.invoke(inputs["input"])

    def generate(inputs: dict[str, Any]) -> str:
        prompt_value = QA_PROMPT.invoke(
            {
                "input": inputs["input"],
                "context": format_context(inputs["context"]),
            }
        )
        prompt = prompt_value.to_string()
        result = llm(prompt)
        if not result:
            return "문서에서 관련 근거를 찾을 수 없습니다."
        return str(result[0].get("generated_text", "")).strip()

    answer_chain = RunnableLambda(generate) | StrOutputParser()
    return RunnablePassthrough.assign(context=retrieve).assign(answer=answer_chain)


def format_context(documents: list[Document]) -> str:
    formatted_documents: list[str] = []

    for doc in documents:
        metadata = {
            "source": doc.metadata.get("source", "unknown"),
            "page": doc.metadata.get("page", "?"),
            "page_content": doc.page_content,
        }
        formatted_documents.append(DOCUMENT_PROMPT.format(**metadata))

    return "\n\n---\n\n".join(formatted_documents)


def format_sources(documents: list[Document]) -> list[str]:
    sources: list[str] = []
    seen: set[tuple[str, str]] = set()

    for doc in documents:
        source = str(doc.metadata.get("source", "unknown"))
        page = str(doc.metadata.get("page", "?"))
        key = (source, page)
        if key in seen:
            continue
        seen.add(key)
        sources.append(f"{source} p.{page}")

    return sources
