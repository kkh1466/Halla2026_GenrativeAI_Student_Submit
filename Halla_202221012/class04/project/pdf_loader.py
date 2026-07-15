from pathlib import Path

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pypdf import PdfReader


def save_uploaded_pdfs(uploaded_files, data_dir):
    """Streamlit에서 업로드한 PDF 파일들을 data 폴더에 저장합니다."""
    saved_paths = []

    for uploaded_file in uploaded_files:
        file_path = Path(data_dir) / uploaded_file.name

        with open(file_path, "wb") as file:
            file.write(uploaded_file.getbuffer())

        saved_paths.append(file_path)

    return saved_paths


def extract_text_from_pdf(pdf_path):
    """PDF 파일에서 페이지별 텍스트를 추출하여 LangChain Document 목록으로 반환합니다."""
    documents = []

    try:
        reader = PdfReader(str(pdf_path))

        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()

            if text:
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": Path(pdf_path).name,
                            "page": page_number,
                        },
                    )
                )

    except Exception as error:
        raise RuntimeError(f"{Path(pdf_path).name} 파일을 읽을 수 없습니다.") from error

    return documents


def load_pdfs(pdf_paths):
    """여러 PDF 파일을 읽어 하나의 Document 목록으로 합칩니다."""
    all_documents = []

    for pdf_path in pdf_paths:
        documents = extract_text_from_pdf(pdf_path)
        all_documents.extend(documents)

    if not all_documents:
        raise ValueError("PDF에서 추출할 수 있는 텍스트가 없습니다.")

    return all_documents


def split_documents(documents, chunk_size=1000, chunk_overlap=200):
    """긴 문서를 작은 chunk로 나누어 검색하기 좋은 형태로 만듭니다."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    return text_splitter.split_documents(documents)
