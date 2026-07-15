import os
from dotenv import load_dotenv

loaded = load_dotenv("api.env")

print("dotenv loaded:", loaded)
print("cwd:", os.getcwd())
print("API KEY:", os.getenv("OPENAI_API_KEY"))

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

def create_vector_db(pdf_path):
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    docs = splitter.split_documents(documents)

    api_key = os.getenv("OPENAI_API_KEY")

    print("API KEY LENGTH:", len(api_key) if api_key else None)

    embedding = OpenAIEmbeddings(
        api_key=api_key
    )

    db = Chroma.from_documents(
        docs,
        embedding,
        persist_directory="chroma_db"
    )

    return db

