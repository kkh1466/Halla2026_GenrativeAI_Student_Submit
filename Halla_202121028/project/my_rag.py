import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

print("불러오기 완료!")
knowledge = """
Retrieval-Augmented Generation, or RAG, is a technique that combines information
retrieval with text generation. Instead of relying only on what a language model
memorized during training, a RAG system first searches a collection of documents
for relevant passages and then gives those passages to the model as context.
This reduces hallucination and lets the model answer questions about private or
up-to-date information.

FAISS stands for Facebook AI Similarity Search. It is an open-source library that
stores embedding vectors and searches for the most similar ones very quickly.
FAISS can handle millions of vectors and is one of the most widely used tools for
similarity search.

An embedding is a list of numbers that represents the meaning of a piece of text.
When two texts have a similar meaning, their embedding vectors are close to each
other.
"""

print("문서 길이:", len(knowledge), "글자")
def split_text(text, chunk_size=200, overlap=50):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

chunks = split_text(knowledge, chunk_size=200, overlap=50)
print("만들어진 조각 개수:", len(chunks))
print("첫 번째 조각:", chunks[0])
print("임베딩 모델 불러오는 중...")
embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")

chunk_embeddings = embedder.encode(chunks, normalize_embeddings=True)
print("임베딩 완료! shape:", chunk_embeddings.shape)
dimension = chunk_embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(chunk_embeddings)

print("FAISS 인덱스 완성! 저장된 벡터 수:", index.ntotal)
def search(query, k=2):
    query_vec = embedder.encode([query], normalize_embeddings=True)
    distances, indices = index.search(query_vec, k)
    results = [chunks[i] for i in indices[0]]
    return results

# 검색 테스트
found = search("What is FAISS?", k=2)
print("\n검색 결과:")
for i, r in enumerate(found):
    print(f"--- 결과 {i} ---")
    print(r)
    print("\nLLM 불러오는 중...")
model_name = "google/flan-t5-base"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

def generate(prompt):
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    outputs = model.generate(**inputs, max_new_tokens=100)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

def ask(question, k=2):
    docs = search(question, k=k)
    context = "\n\n".join(docs)
    prompt = (
        "Answer the question using the context below.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\nAnswer:"
    )
    answer = generate(prompt)
    return answer, docs

# 질문해보기
print("\n=== RAG 질문하기 (종료하려면 'exit' 입력) ===")
while True:
    question = input("\n❓ 질문을 입력하세요: ")
    if question.lower() == "exit":
        break
    answer, docs = ask(question)
    print("💬 답변:", answer)