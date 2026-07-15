import json
import urllib.error
import urllib.request
from typing import Any


OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5:7b-instruct"
FILE_LOOKUP_WORDS = {
    "파일",
    "문서",
    "자료",
    "양식",
    "엑셀",
    "excel",
    "xlsx",
    "xls",
    "pdf",
    "피디에프",
    "찾아",
    "찾아줘",
    "다운로드",
}


def _looks_garbled(value: str) -> bool:
    if not value:
        return False
    sample = value[:1000]
    bad_chars = sample.count("�") + sample.count("\x00")
    return bad_chars >= 5 or (len(sample) > 80 and bad_chars / max(len(sample), 1) > 0.02)


def build_context(results: list[dict[str, Any]], max_chars: int = 12000) -> str:
    parts = []
    used_chars = 0
    for index, item in enumerate(results, start=1):
        metadata = item.get("metadata", {})
        source = metadata.get("source", "unknown")
        source_path = metadata.get("source_path", "")
        content = item.get("content", "").strip()
        if _looks_garbled(content):
            continue

        block = f"[{index}] file: {source}\npath: {source_path}\ncontent:\n{content}\n"
        if used_chars + len(block) > max_chars:
            remaining = max_chars - used_chars
            if remaining <= 500:
                break
            block = block[:remaining]
        parts.append(block)
        used_chars += len(block)
    return "\n---\n".join(parts)


def _is_file_lookup_query(query: str) -> bool:
    query_lower = query.casefold()
    return any(word in query_lower for word in FILE_LOOKUP_WORDS)


def _file_lookup_answer(results: list[dict[str, Any]]) -> str:
    lines = ["요청한 조건과 맞는 참고 문서를 찾았습니다.", ""]
    for index, item in enumerate(results[:3], start=1):
        metadata = item.get("metadata", {})
        source = metadata.get("source") or "출처 없음"
        source_path = metadata.get("source_path") or ""
        file_type = metadata.get("file_type") or ""
        lines.append(f"{index}. {source}")
        details = [value for value in [source_path, file_type] if value]
        if details:
            lines.append(f"   - {' / '.join(details)}")
    lines.append("")
    lines.append("아래 참고 문서 및 다운로드 영역에서 원본 또는 마스킹본을 받을 수 있습니다.")
    return "\n".join(lines)


def call_ollama(prompt: str, model: str = DEFAULT_MODEL) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
            "num_ctx": 16000,
        },
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data.get("response", "")).strip()
    except urllib.error.URLError as exc:
        return f"Ollama에 연결하지 못했습니다. Ollama가 실행 중인지 확인해 주세요.\n\n상세: {exc}"
    except Exception as exc:
        return f"Ollama 답변 생성 중 오류가 발생했습니다.\n\n상세: {exc}"


def generate_answer(query: str, results: list[dict[str, Any]], model: str = DEFAULT_MODEL) -> str:
    if not results:
        return (
            "관련 문서나 메모를 찾지 못했습니다. "
            "파일명, 폴더명, 날짜, 사업명처럼 문서에 들어 있을 만한 단어로 다시 질문해 주세요."
        )

    if _is_file_lookup_query(query):
        strong_file_matches = [
            item
            for item in results
            if item.get("match_type") == "filename" or item.get("metadata", {}).get("source_path")
        ]
        if strong_file_matches:
            return _file_lookup_answer(strong_file_matches)

    context = build_context(results)
    if not context.strip():
        return "관련 파일은 찾았지만 읽을 수 있는 텍스트가 부족합니다. 아래 원본 파일을 다운로드해서 확인해 주세요."

    prompt = f"""너는 RAG 기반 로컬 문서 탐색 보조 AI다.

규칙:
- 반드시 아래 참고 문서 내용만 근거로 답한다.
- 참고 문서에 없는 내용은 추측하지 말고 "문서에서 확인할 수 없습니다"라고 말한다.
- 참고 문서의 file 또는 path에 사용자가 찾는 파일명이 있으면 "찾을 수 없습니다"라고 답하지 말고 찾은 문서로 안내한다.
- 사용자가 파일명이나 폴더명을 물으면 어떤 문서를 찾았는지 먼저 알려준다.
- 답변은 한국어로, 읽기 쉽게 요약한다.
- 중요한 숫자, 날짜, 금액, 파일명은 가능하면 그대로 유지한다.
- 마지막에 근거가 된 파일명을 짧게 적는다.

사용자 질문:
{query}

참고 문서:
{context}

답변:"""
    return call_ollama(prompt, model=model)
