from __future__ import annotations

import re
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
from pypdf import PdfReader

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_community.embeddings import HuggingFaceEmbeddings


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "documents" / "PDF화 된 문서들"
CHROMA_DIR = ROOT / "chroma_db"
FEEDBACK_FILE = ROOT / "data" / "feedback" / "search_feedback.jsonl"
SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".csv"}
IGNORED_DIRECTORY_NAMES = {
    "사인",
    "서명",
    "사진",
    "원본사진",
    "video",
    "videos",
    "movie",
    "movies",
    "demo",
    "demos",
}
EXCEL_WORDS = {"엑셀", "excel", "xlsx", "xls", "스프레드시트"}
PDF_WORDS = {"pdf", "피디에프"}
STOPWORDS = {"파일", "문서", "자료", "달라", "줘", "찾아", "찾아줘", "관련", "에서", "있는", "좀", "보여줘"}


def normalize_for_search(value: str) -> str:
    return re.sub(r"[\s_\-.,()\[\]{}]+", "", value.casefold())


def query_tokens(query: str) -> list[str]:
    raw_tokens = re.findall(r"[0-9A-Za-z가-힣]+", query.casefold())
    tokens = []
    for token in raw_tokens:
        if token in STOPWORDS:
            continue
        if token in EXCEL_WORDS or token in PDF_WORDS:
            tokens.append(token)
            continue
        if len(token) >= 2:
            tokens.append(token)
    return tokens


def looks_garbled(value: str) -> bool:
    if not value:
        return False
    sample = value[:1000]
    bad_chars = sample.count("�") + sample.count("\x00")
    return bad_chars >= 5 or (len(sample) > 80 and bad_chars / max(len(sample), 1) > 0.02)


def feedback_key(query: str) -> str:
    return " ".join(query_tokens(query))


def load_feedback() -> list[dict[str, Any]]:
    if not FEEDBACK_FILE.exists():
        return []
    latest_by_pair = {}
    for line in FEEDBACK_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict):
            continue
        query_key = item.get("query_key") or feedback_key(item.get("query", ""))
        source_path = item.get("source_path")
        if not query_key or not source_path:
            continue
        latest_by_pair[(query_key, source_path)] = {
            **item,
            "query_key": query_key,
            "source_path": source_path,
        }
    return list(latest_by_pair.values())


def save_feedback(query: str, source_path: str, rating: str) -> None:
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    query_key = feedback_key(query)
    records = [
        item
        for item in load_feedback()
        if not (item.get("query_key") == query_key and item.get("source_path") == source_path)
    ]
    record = {
        "query": query.strip(),
        "query_key": query_key,
        "source_path": source_path,
        "rating": rating,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    records.append(record)
    with FEEDBACK_FILE.open("w", encoding="utf-8") as handle:
        for item in records:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


class DocumentRAG:
    def __init__(self, persist_dir: str = str(CHROMA_DIR)):
        self.persist_dir = persist_dir
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection_name = "documents"
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            encode_kwargs={"normalize_embeddings": True},
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=900,
            chunk_overlap=180,
            separators=["\n\n", "\n", " ", ""],
        )

    def _should_skip_path(self, path: Path) -> bool:
        if not path.exists():
            return True
        normalized_parts = {part.casefold() for part in path.parts}
        ignored = {name.casefold() for name in IGNORED_DIRECTORY_NAMES}
        return bool(normalized_parts & ignored)

    def _extract_text_from_pdf(self, file_path: Path) -> str:
        reader = PdfReader(str(file_path))
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"[page {page_number}]\n{text}")
        return "\n\n".join(pages)

    def _extract_text_from_file(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_text_from_pdf(file_path)
        if suffix in {".txt", ".md", ".csv"}:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        return ""

    def iter_supported_files(self, folder: Path | None = None) -> list[Path]:
        folder = folder or DATA_DIR
        if not folder.exists():
            return []
        files = []
        for file_path in sorted(folder.rglob("*")):
            if self._should_skip_path(file_path):
                continue
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_SUFFIXES:
                files.append(file_path.resolve())
        return files

    def ingest_file(self, file_path: Path) -> dict[str, Any]:
        file_path = file_path.resolve()
        if self._should_skip_path(file_path):
            return {"status": "skipped", "file": str(file_path)}
        if file_path.suffix.lower() not in SUPPORTED_SUFFIXES:
            return {"status": "unsupported", "file": str(file_path)}

        try:
            text = self._extract_text_from_file(file_path)
        except Exception as exc:
            return {"status": "error", "file": str(file_path), "error": str(exc)}

        if not text.strip():
            return {"status": "empty", "file": str(file_path)}
        if looks_garbled(text):
            return {"status": "garbled", "file": str(file_path)}

        source_path = file_path.relative_to(ROOT).as_posix()
        title_block = f"문서 제목: {file_path.name}\n문서 경로: {source_path}\n\n"
        chunks = []
        for index, chunk in enumerate(self.text_splitter.split_text(text)):
            chunks.append(
                {
                    "id": f"{source_path.replace('/', '__')}_{index}",
                    "document": title_block + chunk,
                    "metadata": {
                        "source": file_path.name,
                        "source_path": source_path,
                        "file_type": file_path.suffix.lower(),
                        "chunk_index": index,
                    },
                }
            )

        existing = self.collection.get(where={"source_path": source_path}, include=["documents"])
        if existing.get("ids"):
            self.collection.delete(ids=existing["ids"])

        embeddings = self.embeddings.embed_documents([chunk["document"] for chunk in chunks])
        self.collection.add(
            ids=[chunk["id"] for chunk in chunks],
            embeddings=embeddings,
            metadatas=[chunk["metadata"] for chunk in chunks],
            documents=[chunk["document"] for chunk in chunks],
        )
        return {"status": "ok", "chunks": len(chunks), "file": str(file_path)}

    def ingest_folder(self, folder: Path | None = None) -> list[dict[str, Any]]:
        return [self.ingest_file(file_path) for file_path in self.iter_supported_files(folder)]

    def reset(self) -> dict[str, str]:
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
        return {"status": "ok", "message": "collection reset"}

    def get_status(self, folder: Path | None = None) -> dict[str, Any]:
        supported_files = self.iter_supported_files(folder)
        indexed = self.collection.get(include=["metadatas"])
        metadatas = indexed.get("metadatas", [])
        indexed_files = {item.get("source_path") for item in metadatas if item and item.get("source_path")}
        return {
            "documents_folder": str((folder or DATA_DIR).resolve()),
            "supported_files_found": len(supported_files),
            "indexed_files": len(indexed_files),
            "indexed_chunks": len(indexed.get("ids", [])),
            "supported_extensions": sorted(SUPPORTED_SUFFIXES),
            "ignored_directories": sorted(IGNORED_DIRECTORY_NAMES),
        }

    def _file_match_score(self, file_path: Path, tokens: list[str], query: str) -> float:
        relative = file_path.relative_to(ROOT).as_posix()
        file_name = normalize_for_search(file_path.name)
        haystack = normalize_for_search(f"{file_path.name} {relative}")
        score = 0.0
        for token in tokens:
            normalized = normalize_for_search(token)
            if not normalized:
                continue
            if normalized in haystack:
                score += 3.0
            if normalized in file_name:
                score += 3.0
            try:
                folder_parts = file_path.relative_to(DATA_DIR).parts[:-1]
            except ValueError:
                folder_parts = file_path.parts[:-1]
            if any(normalized in normalize_for_search(part) for part in folder_parts):
                score += 2.0

        query_lower = query.casefold()
        if any(word in query_lower for word in EXCEL_WORDS) and file_path.suffix.lower() in {".xlsx", ".xls", ".csv"}:
            score += 2.0
        if any(word in query_lower for word in PDF_WORDS) and file_path.suffix.lower() == ".pdf":
            score += 2.0
        return min(score, 10.0)

    def _feedback_score(self, query: str, source_path: str) -> float:
        current_tokens = set(query_tokens(query))
        current_key = feedback_key(query)
        if not current_tokens and not current_key:
            return 0.0

        score = 0.0
        for item in load_feedback():
            if item.get("source_path") != source_path:
                continue
            rating = item.get("rating")
            if rating not in {"positive", "negative"}:
                continue

            item_key = item.get("query_key") or feedback_key(item.get("query", ""))
            item_tokens = set(item_key.split())
            if not item_tokens and item_key != current_key:
                continue

            if item_key == current_key:
                overlap = 1.0
            else:
                overlap = len(current_tokens & item_tokens) / max(len(current_tokens | item_tokens), 1)
            if overlap < 0.35:
                continue

            weight = 6.0 if item_key == current_key else 4.0 * overlap
            score += weight if rating == "positive" else -weight
        return max(-6.0, min(6.0, score))

    def _file_matches(self, query: str, top_k: int) -> list[dict[str, Any]]:
        tokens = query_tokens(query)
        if not tokens:
            return []

        scored = []
        for file_path in self.iter_supported_files():
            relative = file_path.relative_to(ROOT).as_posix()
            score = self._file_match_score(file_path, tokens, query)
            score += self._feedback_score(query, relative)
            if score <= 0:
                continue
            scored.append(
                (
                    score,
                    str(relative),
                    {
                        "content": f"파일명/폴더명으로 찾은 문서입니다.\n원본 파일: {file_path.name}\n파일 위치: {relative}",
                        "metadata": {
                            "source": file_path.name,
                            "source_path": relative,
                            "file_type": file_path.suffix.lower(),
                            "chunk_index": 0,
                        },
                        "distance": max(0.0, 1.0 - min(score / 30.0, 0.99)),
                        "match_type": "filename",
                        "rank_score": score,
                    },
                )
            )
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored[:top_k]]

    def _format_query_results(self, query_result: dict[str, Any]) -> list[dict[str, Any]]:
        docs = []
        documents = query_result.get("documents", [[]])[0]
        metadatas = query_result.get("metadatas", [[]])[0]
        distances = query_result.get("distances", [[]])[0]
        for index, document in enumerate(documents):
            docs.append(
                {
                    "content": document,
                    "metadata": metadatas[index] if index < len(metadatas) else {},
                    "distance": float(distances[index]) if index < len(distances) else 1.0,
                    "match_type": "content",
                }
            )
        return docs

    def search(
        self,
        query: str,
        top_k: int = 5,
        previous_references: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return []

        filename_results = self._file_matches(query, top_k=top_k)
        query_embedding = self.embeddings.embed_query(query)
        raw_results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=max(top_k * 3, 10),
            include=["documents", "metadatas", "distances"],
        )
        content_results = self._format_query_results(raw_results)

        merged = []
        seen = set()
        for item in filename_results + content_results:
            metadata = item.get("metadata", {})
            key = (metadata.get("source_path"), metadata.get("chunk_index"))
            if key in seen:
                continue
            if item.get("match_type") == "content" and looks_garbled(item.get("content", "")):
                continue
            source_path = metadata.get("source_path", "")
            feedback_boost = self._feedback_score(query, source_path)
            if feedback_boost:
                item["feedback_score"] = feedback_boost
                if item.get("match_type") == "filename":
                    item["rank_score"] = item.get("rank_score", 0.0) + feedback_boost
                    item["distance"] = max(0.0, item.get("distance", 1.0) - feedback_boost / 40.0)
                else:
                    item["distance"] = max(0.0, item.get("distance", 1.0) - feedback_boost / 10.0)
            seen.add(key)
            merged.append(item)
        merged.sort(
            key=lambda item: (
                float(item.get("distance", 1.0)),
                -float(item.get("rank_score", 0.0)),
                item.get("metadata", {}).get("source_path", ""),
            )
        )
        return merged[:top_k]

    def summarize(self, query: str, top_k: int = 5) -> str:
        hits = self.search(query, top_k=top_k)
        if not hits:
            return "관련 문서를 찾지 못했습니다."
        parts = []
        for index, item in enumerate(hits, start=1):
            metadata = item.get("metadata", {})
            parts.append(f"{index}. {metadata.get('source', '출처 없음')}\n{item.get('content', '')[:1200]}")
        return "관련 문서에서 찾은 내용입니다.\n\n" + "\n\n---\n\n".join(parts)
