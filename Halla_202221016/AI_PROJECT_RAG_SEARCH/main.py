import json
import re
import shutil
import threading
import time
import hashlib
from pathlib import Path
from typing import Any

import pypdf
import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.rag_system import DATA_DIR, DocumentRAG

app = FastAPI(title="Document RAG System")
# Initialize DocumentRAG globally, with error handling for better diagnostics
try:
    rag = DocumentRAG()
except Exception as e:
    print(f"ERROR: Failed to initialize DocumentRAG: {e}")
    import traceback
    traceback.print_exc()
    # Re-raise the exception to ensure the application fails to start if RAG is not working
    raise
ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / ".ingested_files.json"
SUPPORTED_SUFFIXES = {".pdf", ".xlsx", ".xls", ".doc", ".docx", ".hwp", ".hwpx", ".pptx", ".ppt", ".txt", ".md", ".csv"}
PROGRESS_LOCK = threading.Lock()
INGEST_PROGRESS: dict[str, Any] = {
    "is_running": False,
    "total_files": 0,
    "processed_files": 0,
    "percent": 100.0,
    "current_file": None,
    "last_result": None,
    "last_error": None,
    "last_started_at": None,
    "last_finished_at": None,
}

def looks_garbled(content: str) -> bool:
    """Checks if the content appears to be garbled."""
    # High count of replacement characters or null bytes is a strong indicator.
    return content.count("") >= 5 or content.count("\x00") > 0


def check_pdf_content(file_path: Path) -> str | None:
    """Extracts text from the first page of a PDF to check for garbling."""
    try:
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            if reader.pages:
                # Extract text from the first page
                return reader.pages[0].extract_text()
    except Exception:
        # If pypdf fails, we can't check, so we assume it's not garbled for now.
        return None
    return None


def get_rag_source_hash() -> str | None:
    """Calculates the MD5 hash of the rag_system.py source file."""
    rag_system_path = ROOT / "src" / "rag_system.py"
    if rag_system_path.exists():
        return hashlib.md5(rag_system_path.read_bytes()).hexdigest()
    return None

def _load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(data: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _collect_supported_files(folder: Path) -> list[Path]:
    return [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES]


def _file_signature(file_path: Path) -> dict[str, Any]:
    stat = file_path.stat()
    return {
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
    }


def _progress_update(**changes: Any) -> None:
    with PROGRESS_LOCK:
        INGEST_PROGRESS.update(changes)
        total = INGEST_PROGRESS["total_files"]
        processed = INGEST_PROGRESS["processed_files"]
        INGEST_PROGRESS["percent"] = round((processed / total) * 100, 2) if total else 100.0


def _progress_increment_processed() -> None:
    with PROGRESS_LOCK:
        INGEST_PROGRESS["processed_files"] += 1
        total = INGEST_PROGRESS["total_files"]
        processed = INGEST_PROGRESS["processed_files"]
        INGEST_PROGRESS["percent"] = round((processed / total) * 100, 2) if total else 100.0


def _ingest_changed_files(files: list[Path]) -> list[dict[str, Any]]:
    state_data = _load_state()
    # Handle old format or corrupted state
    if isinstance(state_data, list):
        state = {path: {} for path in state_data}
    else:
        state = state_data.get("files", {})

    current_state = {str(path.resolve()): _file_signature(path) for path in files}
    changed_files = [
        Path(file_str)
        for file_str, signature in current_state.items()
        if state.get(file_str) != signature
    ]
    results = []

    _progress_update(
        is_running=True,
        total_files=len(changed_files),
        processed_files=0,
        current_file=None,
        last_result=None,
        last_error=None,
        last_started_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        last_finished_at=None,
    )

    try:
        for file_path in sorted(changed_files):
            _progress_update(current_file=str(file_path))
            try:
                result = rag.ingest_file(file_path)
                results.append(result)
                if result.get("status") in {"ok", "empty", "skipped", "unsupported"}:
                    state[str(file_path.resolve())] = _file_signature(file_path)
                _progress_update(last_result=result)
            except Exception as exc:
                error = {"file": str(file_path), "error": str(exc)}
                results.append({"status": "error", **error})
                _progress_update(last_error=error)
            finally:
                _progress_increment_processed()
    finally:
        _progress_update(
            is_running=False,
            current_file=None,
            last_finished_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        # 성공적으로 처리된 파일들의 상태를 저장합니다.
        current_hash = get_rag_source_hash()
        new_file_state = {path: state[path] for path in current_state if path in state}
        _save_state({"source_hash": current_hash, "files": new_file_state})
    return results


def _background_ingest_loop(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            _ingest_changed_files(_collect_supported_files(DATA_DIR))
        except Exception as exc:
            _progress_update(last_error={"error": str(exc), "where": "background_ingest_loop"})
        time.sleep(5)


@app.on_event("startup")
def start_background_ingest() -> None:
    if getattr(app.state, "background_thread", None) is not None:
        return

    current_hash = get_rag_source_hash()
    state = _load_state()
    stored_hash = state.get("source_hash")

    if current_hash is not None and current_hash != stored_hash:
        print(f"Code change detected (hash: {current_hash[:7]}). Triggering full re-index.")
        rag.reset()
        if STATE_FILE.exists():
            STATE_FILE.unlink()

    if getattr(app.state, "background_thread", None) is None:
        stop_event = threading.Event()
        thread = threading.Thread(target=_background_ingest_loop, args=(stop_event,), daemon=True)
        thread.start()
        app.state.stop_event = stop_event


@app.on_event("shutdown")
def shutdown_background_ingest():
    stop_event = getattr(app.state, "stop_event", None)
    if stop_event:
        stop_event.set()
    thread = getattr(app.state, "background_thread", None)
    if thread:
        thread.join(timeout=5)


@app.get("/")
def read_root() -> dict:
    return {"message": "Document RAG server is running"}


@app.get("/status")
def get_status() -> dict:
    status = rag.get_status()
    with PROGRESS_LOCK:
        learning = dict(INGEST_PROGRESS)
    status["learning_progress"] = learning
    status["learning_rate"] = f"{learning['percent']}%"
    return status


@app.get("/learning-status")
def get_learning_status() -> dict:
    with PROGRESS_LOCK:
        return dict(INGEST_PROGRESS)


@app.post("/upload")
async def upload_document(file: UploadFile = File(...), category: str = Form("general")) -> JSONResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    target_dir = DATA_DIR / category
    target_dir.mkdir(parents=True, exist_ok=True)
    save_path = target_dir / file.filename

    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # PDF 파일의 경우, 텍스트가 깨져 있는지 미리 확인합니다.
    if save_path.suffix.lower() == ".pdf":
        extracted_text = check_pdf_content(save_path)
        if extracted_text and looks_garbled(extracted_text):
            return JSONResponse(content={
                "status": "ok",
                "file": file.filename,
                "result": {"status": "garbled", "chunks": 0}
            })

    result = rag.ingest_file(save_path)

    state_data = _load_state()
    if isinstance(state_data, list):
        file_state = {path: {} for path in state_data}
    else:
        file_state = state_data.get("files", {})

    file_state[str(save_path.resolve())] = _file_signature(save_path)
    current_hash = get_rag_source_hash()
    _save_state({"source_hash": current_hash, "files": file_state})

    return JSONResponse(content={"status": "ok", "file": file.filename, "result": result})


@app.post("/ingest")
def ingest_folder(background_tasks: BackgroundTasks) -> dict:
    with PROGRESS_LOCK:
        if INGEST_PROGRESS["is_running"]:
            raise HTTPException(status_code=409, detail="An ingestion task is already in progress.")

    background_tasks.add_task(_ingest_changed_files, _collect_supported_files(DATA_DIR))
    return {"status": "ok", "message": "Ingestion task started in the background."}


@app.post("/reset")
def reset_and_reingest(background_tasks: BackgroundTasks) -> dict:
    """
    Resets the entire system by clearing the vector database and the ingestion state,
    then starts a full re-ingestion of all documents.
    """
    with PROGRESS_LOCK:
        if INGEST_PROGRESS["is_running"]:
            raise HTTPException(status_code=409, detail="An ingestion task is already in progress. Cannot reset now.")

    # 1. Clear vector DB
    rag.reset()

    # 2. Delete state file
    if STATE_FILE.exists():
        STATE_FILE.unlink()

    # 3. Trigger full re-ingestion in the background
    background_tasks.add_task(_ingest_changed_files, _collect_supported_files(DATA_DIR))

    return {"status": "ok", "message": "System reset and re-ingestion started in the background."}

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    previous_references: list[dict] = Field(default_factory=list)


@app.post("/search")
def search_documents(request: SearchRequest) -> dict:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query is required")
    results = rag.search(
        query=request.query, top_k=request.top_k, previous_references=request.previous_references
    )
    return {"query": request.query, "results": results}


@app.post("/summarize")
def summarize_documents(query: str) -> dict:
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query is required")
    return {"query": query, "summary": rag.summarize(query)}


@app.post("/generate-template")
def generate_template(
    template_type: str = Form("report"),
    title: str = Form("제목 없음"),
    summary: str = Form("요약 내용을 입력하세요"),
    budget: str = Form("예산 정보 없음"),
    author: str = Form("작성자 미지정"),
) -> dict:
    slug = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", title).strip("_") or "report"
    output_dir = DATA_DIR / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    save_path = output_dir / f"{slug}.md"

    content = f"""# {title}

## 작성자
{author}

## 유형
{template_type}

## 요약
{summary}

## 예산
{budget}

## 작성 가이드
- 핵심 목적을 먼저 정리한다.
- 필요한 수치와 근거를 포함한다.
- 이후 보고서 템플릿으로 재사용할 수 있다.
"""
    save_path.write_text(content, encoding="utf-8")
    result = rag.ingest_file(save_path)
    return {"status": "ok", "file": str(save_path.name), "result": result}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
