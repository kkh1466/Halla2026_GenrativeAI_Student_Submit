import faiss
from sentence_transformers import SentenceTransformer
from flask import Flask, request, render_template_string

# ===== 1. K-pop 노래 정보 데이터 =====
songs = [
    "다이너마이트(Dynamite) - 방탄소년단(BTS). 2020년 발매. 디스코팝 장르로, 코로나 시기에 위로를 주는 밝고 경쾌한 곡. 빌보드 핫100 1위 달성.",
    "How You Like That - 블랙핑크(BLACKPINK). 2020년 발매. 강렬한 비트와 파워풀한 랩이 특징인 걸크러시 콘셉트 곡.",
    "Cupid - 피프티 피프티(FIFTY FIFTY). 2023년 발매. 레트로 신스팝 감성의 사랑 노래로 미국에서 역주행 인기를 얻음.",
    "Antifragile - 르세라핌(LE SSERAFIM). 2022년 발매. 자신감과 강인함을 노래하는 하이틴 팝 곡.",
    "OMG - 뉴진스(NewJeans). 2023년 발매. Y2K 감성의 청량한 팝 곡으로 첫사랑의 설렘을 표현.",
    "Ditto - 뉴진스(NewJeans). 2022년 발매. 몽환적인 신스팝 사운드로 추억과 그리움을 노래함.",
    "Super Shy - 뉴진스(NewJeans). 2023년 발매. 좋아하는 사람 앞에서 수줍은 감정을 표현한 업템포 팝 곡.",
    "Killing Voice - 스트레이 키즈(Stray Kids). 강렬한 힙합 비트와 자작곡 프로듀싱으로 유명한 그룹의 대표곡 스타일.",
    "Spicy - 에스파(aespa). 2023년 발매. 매혹적이고 당당한 콘셉트의 신스팝 곡.",
    "Next Level - 에스파(aespa). 2021년 발매. SF적 세계관과 강렬한 사운드가 특징인 메타버스 콘셉트 곡.",
    "Attention - 뉴진스(NewJeans). 2022년 데뷔곡. 상큼하고 청량한 R&B 팝 사운드.",
    "Free Fall - 아이브(IVE). 몽환적이고 세련된 신스팝 사운드가 특징.",
    "I AM - 아이브(IVE). 2022년 발매. 자기 확신과 자존감을 노래하는 당당한 곡.",
    "LOVE DIVE - 아이브(IVE). 2022년 발매. 화려한 훅과 중독성 있는 멜로디의 팝 곡.",
    "Seven - 정국(Jung Kook, BTS). 2023년 발매. 여름 감성의 팝 댄스곡으로 솔로 데뷔곡.",
]

# ===== 2. 임베딩 모델 (한국어 지원) =====
print("한국어 임베딩 모델 불러오는 중...")
embedder = SentenceTransformer("jhgan/ko-sroberta-multitask")
song_embeddings = embedder.encode(songs, normalize_embeddings=True)

# ===== 3. FAISS 인덱스 =====
dimension = song_embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(song_embeddings)

print("K-pop 검색기 준비 완료!")

# ===== 4. 검색 함수 =====
def search(query, k=3):
    query_vec = embedder.encode([query], normalize_embeddings=True)
    distances, indices = index.search(query_vec, k)
    results = [songs[i] for i in indices[0]]
    return results

# ===== 5. Flask 웹 서버 =====
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>K-pop 노래 검색기</title>
    <style>
        body { font-family: sans-serif; max-width: 700px; margin: 50px auto; padding: 0 20px; background: #f7f7f8; }
        h1 { color: #2b2b2b; }
        form { display: flex; gap: 10px; margin-bottom: 30px; }
        input[type=text] { flex: 1; padding: 12px; font-size: 16px; border: 1px solid #ccc; border-radius: 8px; }
        button { padding: 12px 20px; font-size: 16px; background: #ff4a8d; color: white; border: none; border-radius: 8px; cursor: pointer; }
        button:hover { background: #e03a7a; }
        .result { background: white; padding: 16px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); margin-bottom: 12px; }
    </style>
</head>
<body>
    <h1>🎵 K-pop 노래 검색기</h1>
    <form method="POST">
        <input type="text" name="question" placeholder="예: 청량한 여름 노래 추천해줘" value="{{ question or '' }}">
        <button type="submit">검색</button>
    </form>

    {% if results %}
    <h3>🔎 검색 결과</h3>
    {% for r in results %}
    <div class="result">{{ r }}</div>
    {% endfor %}
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    results = []
    question = None
    if request.method == "POST":
        question = request.form["question"]
        results = search(question, k=3)
    return render_template_string(HTML_TEMPLATE, results=results, question=question)

if __name__ == "__main__":
    app.run(debug=False, port=5001)