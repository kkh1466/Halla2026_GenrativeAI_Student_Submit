import faiss
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from flask import Flask, request, render_template_string

# ===== 1. 문서 준비 =====
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

# ===== 2. 청크 분할 =====
def split_text(text, chunk_size=200, overlap=50):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

chunks = split_text(knowledge, chunk_size=200, overlap=50)

# ===== 3. 임베딩 + FAISS =====
print("임베딩 모델 불러오는 중...")
embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
chunk_embeddings = embedder.encode(chunks, normalize_embeddings=True)

dimension = chunk_embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(chunk_embeddings)

# ===== 4. 검색 함수 =====
def search(query, k=2):
    query_vec = embedder.encode([query], normalize_embeddings=True)
    distances, indices = index.search(query_vec, k)
    results = [chunks[i] for i in indices[0]]
    return results

# ===== 5. LLM 준비 =====
print("LLM 불러오는 중...")
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

print("RAG 준비 완료! 웹 서버를 시작합니다...")

# ===== 6. Flask 웹 서버 =====
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>내 RAG 검색기</title>
    <style>
        body { font-family: sans-serif; max-width: 700px; margin: 50px auto; padding: 0 20px; background: #f7f7f8; }
        h1 { color: #2b2b2b; }
        form { display: flex; gap: 10px; margin-bottom: 30px; }
        input[type=text] { flex: 1; padding: 12px; font-size: 16px; border: 1px solid #ccc; border-radius: 8px; }
        button { padding: 12px 20px; font-size: 16px; background: #4a4af4; color: white; border: none; border-radius: 8px; cursor: pointer; }
        button:hover { background: #3a3adf; }
        .answer-box { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); margin-bottom: 20px; }
        .answer-box h3 { margin-top: 0; color: #4a4af4; }
        .chunk { background: #eef; padding: 12px; border-radius: 8px; margin-top: 10px; font-size: 14px; color: #444; }
    </style>
</head>
<body>
    <h1>🔍 내가 만든 RAG 검색기</h1>
    <form method="POST">
        <input type="text" name="question" placeholder="질문을 입력하세요 (영어)" value="{{ question or '' }}">
        <button type="submit">검색</button>
    </form>

    {% if answer %}
    <div class="answer-box">
        <h3>💬 답변</h3>
        <p>{{ answer }}</p>
    </div>
    <div class="answer-box">
        <h3>📚 근거가 된 조각</h3>
        {% for doc in docs %}
        <div class="chunk">{{ doc }}</div>
        {% endfor %}
    </div>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    answer = None
    docs = []
    question = None
    if request.method == "POST":
        question = request.form["question"]
        answer, docs = ask(question)
    return render_template_string(HTML_TEMPLATE, answer=answer, docs=docs, question=question)

if __name__ == "__main__":
    app.run(debug=False, port=5000)