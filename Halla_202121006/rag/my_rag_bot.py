import warnings
warnings.filterwarnings("ignore")

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# ==========================================
# 1단계 · PDF 데이터 준비 📄
# ==========================================
print("1) PDF 리포트를 읽어오는 중입니다...")
# 파일 이름이 맞는지 확인하세요!
loader = PyPDFLoader("UCL_Mini-Tech-Report_2026_DIGITAL_v1.pdf")
chunks = loader.load_and_split()
print(f"   -> 완료! 총 {len(chunks)}개의 페이지 조각이 준비되었습니다.")

# ==========================================
# 2단계 · 임베딩 & 벡터 저장소 준비 🔢
# ==========================================
print("2) AI 모델(임베딩)을 준비하는 중입니다...")
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    encode_kwargs={"normalize_embeddings": True}
)
vectorstore = FAISS.from_documents(chunks, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
print("   -> 완료! 데이터 저장 완료.")

# ==========================================
# 3단계 · LLM(생성 모델) 준비 🤖
# ==========================================
print("3) AI 모델(언어 모델)을 불러오는 중입니다... (잠시만 기다려주세요!)")
# 메모리 오류 방지를 위해 가벼운 'small' 모델 사용
model_name = "google/flan-t5-small" 
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

def generate(prompt):
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    outputs = model.generate(**inputs, max_new_tokens=256)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)
print("   -> 완료! 이제 질문할 준비가 끝났습니다.\n")

# ==========================================
# 4단계 · 대화형 루프 (질문 대기) 🙋
# ==========================================
print("=" * 60)
print("⚽ 나만의 UCL 테크니컬 리포트 RAG 봇 가동 시작! ⚽")
print("⚽ (종료하려면 'exit' 또는 'quit'을 입력하세요) ⚽")
print("=" * 60)

while True:
    user_input = input("\n❓ 질문을 입력하세요: ")
    
    # 종료 조건
    if user_input.lower() in ['exit', 'quit']:
        print("💬 봇을 종료합니다. 다음에 또 만나요! 👋")
        break
    
    # RAG 흐름: 검색 -> 컨텍스트 조립 -> LLM 답변
    docs = retriever.invoke(user_input)
    context = "\n\n".join(d.page_content for d in docs)
    prompt = (
        "Answer the question using the context below.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {user_input}\nAnswer:"
    )
    
    answer = generate(prompt)
    print(f"💬 답변: {answer}")
    print("-" * 40)