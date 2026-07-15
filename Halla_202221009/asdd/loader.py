from __future__ import annotations

from pathlib import Path
from typing import Iterable

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_pdf_documents(pdf_paths: Iterable[str | Path]) -> list[Document]:
    """Load PDF files and keep source/page metadata for citations."""
    documents: list[Document] = []

    for pdf_path in pdf_paths:
        path = Path(pdf_path)
        loader = PyPDFLoader(str(path))
        loaded_pages = loader.load()

        for page in loaded_pages:
            page.metadata["source"] = path.name
            if "page" in page.metadata:
                page.metadata["page"] = int(page.metadata["page"]) + 1
            documents.append(page)

    return documents


def split_documents(
    documents: list[Document],
    chunk_size: int = 900,
    chunk_overlap: int = 150,
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documents)
