import streamlit as st
import requests
import base64
import os

# =========================
# 페이지 설정
# =========================
st.set_page_config(
    page_title="Date RAG",
    page_icon="💖",
    layout="wide"
)

# =========================
# 마스코트 이미지 로드 (base64)
# =========================
MASCOT_PATH = os.path.join(os.path.dirname(__file__), "mascot.png")

def load_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

mascot_b64 = load_image_base64(MASCOT_PATH)


# =========================
# 폰트 + CSS 스타일
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;500;700;800&display=swap');

* {
    font-family: 'Pretendard', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #fff0f5 0%, #e6f7ff 60%, #eaf3ff 100%);
}

#MainMenu, header, footer {visibility: hidden;}

.block-container {
    padding-top: 1.5rem;
    max-width: 1200px;
}

/* ---------- 네비게이션 바 ---------- */
.navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: white;
    border-radius: 999px;
    padding: 14px 28px;
    box-shadow: 0 8px 24px rgba(255, 77, 109, 0.12);
    margin-bottom: 30px;
}
.navbar .logo {
    font-weight: 800;
    font-size: 20px;
    color: #2b3a67;
    display: flex;
    align-items: center;
    gap: 8px;
}
.navbar .logo span {
    color: #ff4d6d;
}
.navbar .menu {
    display: flex;
    gap: 30px;
    font-weight: 600;
    color: #444;
    font-size: 15px;
}
.navbar .cta {
    background: linear-gradient(135deg, #ff8fa3, #ff4d6d);
    color: white;
    padding: 10px 20px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 14px;
    white-space: nowrap;
}

/* ---------- 히어로 ---------- */
.hero-title {
    font-size: 46px;
    font-weight: 800;
    color: #2b3a67;
    line-height: 1.3;
    margin-bottom: 6px;
}
.hero-title .pink { color: #ff4d6d; }
.hero-sub {
    font-size: 16px;
    color: #6a6f9c;
    font-weight: 600;
    margin-bottom: 18px;
}
.hero-desc {
    background: white;
    border-radius: 18px;
    padding: 18px 22px;
    box-shadow: 0 8px 20px rgba(255, 77, 109, 0.10);
    color: #555;
    font-size: 15px;
    line-height: 1.6;
    display: inline-block;
}

/* ---------- 마스코트(블롭) ---------- */
.mascot-wrap {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 340px;
}
.mascot-img {
    width: 800px;      
    height: auto;
    filter: drop-shadow(0 20px 30px rgba(255, 150, 180, 0.35));
    animation: float 3.5s ease-in-out infinite;
}
@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-12px); }
}
.bubble {
    position: absolute;
    background: white;
    border-radius: 16px;
    padding: 10px 16px;
    box-shadow: 0 8px 18px rgba(0,0,0,0.08);
    font-size: 13px;
    font-weight: 600;
    color: #444;
}
.bubble-1 { top: 10px; left: 0px; }
.bubble-2 {
    top: 40px;
    right: -10px;
    text-align: left;
    line-height: 1.5;
    font-weight: 500;
}
.bubble-2 b { color: #ff4d6d; }

/* ---------- 기능 카드 ---------- */
.feat-card {
    background: white;
    border-radius: 20px;
    padding: 26px 16px;
    text-align: center;
    box-shadow: 0 8px 20px rgba(80, 90, 160, 0.08);
    transition: 0.25s;
    height: 100%;
}
.feat-card:hover { transform: translateY(-6px); }
.feat-icon {
    width: 60px; height: 60px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 14px auto;
    font-size: 26px;
}
.feat-title {
    font-weight: 700;
    color: #2b3a67;
    margin-bottom: 6px;
    font-size: 16px;
}
.feat-desc {
    color: #888;
    font-size: 12.5px;
    line-height: 1.5;
}
.feat-line { color: #ff4d6d; font-size: 12px; margin-top: 8px; }

/* ---------- 하단 채팅 / 인기질문 카드 ---------- */
.panel-title {
    font-weight: 800;
    color: #ff4d6d;
    font-size: 16px;
    margin-bottom: 4px;
}
.panel-title.blue { color: #2b6fff; }
.panel-spacer { height: 22px; width: 100%; }

/* 진짜 컨테이너(key)로 감싼 카드 배경 - 스크롤 없이 내용만큼 자연스럽게 늘어남 */
.st-key-chat_panel, .st-key-faq_panel {
    background: white;
    border-radius: 22px;
    padding: 24px 26px;
    box-shadow: 0 8px 22px rgba(80, 90, 160, 0.08);
}

/* chat_input 대신 쓰는 커스텀 입력창(text_input + 전송버튼)을 말풍선 pill 스타일로 */
div[data-testid="stForm"] {
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}
div[data-testid="stTextInput"] input {
    border-radius: 999px !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    background: #f7f7f9 !important;
    padding: 10px 18px !important;
    font-size: 14px;
}
div[data-testid="stTextInput"] input:focus {
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}
div[data-testid="stTextInput"] > div {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}
div[data-testid="stFormSubmitButton"] > button {
    border-radius: 50% !important;
    width: 42px;
    height: 42px;
    min-height: 42px;
    padding: 0 !important;
    background: #ff4d6d !important;
    color: white !important;
    border: none !important;
    font-weight: 700;
    margin-bottom: 0 !important;
}
div[data-testid="stFormSubmitButton"] > button:hover {
    background: #ff2e52 !important;
}

/* 버튼 스타일 수정 (여백 추가 및 텍스트 줄바꿈 방지) */
div.stButton > button {
    border-radius: 999px;
    border: 1px solid #ff4d6d;
    background: white;
    color: #ff4d6d;
    padding: 10px 16px;
    font-weight: 600;
    width: 100%;
    margin-bottom: 6px; /* 버튼 간의 수직 틈새(여백) - 좁게 조정 */
    white-space: nowrap; /* 텍스트가 강제로 한 줄로 나오도록 설정 */
    text-overflow: ellipsis;
    overflow: hidden;
}
div.stButton > button:hover {
    background: #ff4d6d;
    color: white;
    border: 1px solid #ff4d6d;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 상태 초기화
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "quick" not in st.session_state:
    st.session_state.quick = None

# =========================
# 네비게이션 바
# =========================
st.markdown("""
<div class="navbar">
    <div class="logo">💕 Date <span>RAG</span></div>
    <div class="menu">
        <div>홈</div><div>데이트 코스</div><div>사용 방법</div><div>소개</div>
    </div>
    <div class="cta">챗봇 시작하기 💕</div>
</div>
""", unsafe_allow_html=True)

# =========================
# 히어로 섹션
# =========================
hero_l, hero_r = st.columns([1.1, 1])

with hero_l:
    st.markdown("""
    <div class="hero-title">오늘, 우리<br><span class="pink">어디로 데이트 갈까?</span></div>
    <div class="hero-sub">💗 RAG 기반 데이터 추천 챗봇</div>
    <div class="hero-desc">
        당신의 취향과 상황에 딱 맞는<br>
        서울과 강릉의 데이트 코스를 AI가 찾아드려요! 💖
    </div>
    """, unsafe_allow_html=True)

with hero_r:
    if mascot_b64:
        mascot_tag = f'<img class="mascot-img" src="data:image/png;base64,{mascot_b64}">'
    else:
        mascot_tag = '<div style="font-size:120px;">🐣</div>'

    st.markdown(f"""
    <div class="mascot-wrap">
        <div class="bubble bubble-1">❤️</div>
        {mascot_tag}
        <div class="bubble bubble-2">
            안녕하세요! 💕<br>
            저는 <b>데이트 코스 챗봇</b>이에요!<br>
            무엇을 도와드릴까요?
        </div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# =========================
# 기능 카드 (아이콘)
# =========================
features = [
    ("📍", "#ffe1e8", "맞춤 데이트 추천", "당신의 취향, 날씨, 시간, 예산까지 고려한 맞춤 코스를 추천해요.", "❤️"),
    ("💬", "#e1ecff", "실시간 챗봇 상담", "궁금한 점을 물어보면 AI가 바로바로 답해드려요.", "💙"),
    ("📄", "#ffe1e8", "RAG 기반 정보 제공", "신뢰할 수 있는 최신 정보만 모아 정확하게 알려드려요.", "❤️"),
    ("📅", "#e1ecff", "다양한 테마 제공", "계절, 기념일, 취향별 다양한 테마로 특별한 데이트를 계획해보세요.", "💙"),
]

cols = st.columns(4)
for i, (icon, bg, title, desc, line) in enumerate(features):
    with cols[i]:
        st.markdown(f"""
        <div class="feat-card">
            <div class="feat-icon" style="background:{bg};">{icon}</div>
            <div class="feat-title">{title}</div>
            <div class="feat-desc">{desc}</div>
            <div class="feat-line">— {line} —</div>
        </div>
        """, unsafe_allow_html=True)

st.write("")
st.write("")

# =========================
# 채팅 + 인기 질문 (2단 레이아웃)
# =========================
chat_col, faq_col = st.columns([1.3, 1], gap="large")

# 왼쪽: 실시간 채팅 패널 (container(key=...)로 진짜 하나의 카드로 묶음, 스크롤 없음)
with chat_col:
    with st.container(key="chat_panel"):
        st.markdown(
            '<div class="panel-title blue">💙 무엇이든 물어보세요</div><div class="panel-spacer"></div>',
            unsafe_allow_html=True,
        )

        # 채팅 메시지 출력
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # 채팅 입력창 (chat_input 대신 text_input+버튼 폼 -> 카드 밖으로 튀어나가지 않음)
        with st.form(key="chat_form", clear_on_submit=True):
            input_col, btn_col = st.columns([9, 1])
            with input_col:
                typed_text = st.text_input(
                    "질문",
                    placeholder="예) 비 오는 날 실내 데이트 추천해줘!",
                    label_visibility="collapsed",
                )
            with btn_col:
                submitted = st.form_submit_button("➤")

        user_input = typed_text if submitted and typed_text else None

        # 인기 질문 자동 입력 처리
        if st.session_state.quick:
            user_input = st.session_state.quick
            st.session_state.quick = None

        # API 요청 기능
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})

            with st.spinner("AI가 여행 코스 찾는 중... ✈️"):
                try:
                    res = requests.post(
                        "http://127.0.0.1:8000/chat",
                        json={"question": user_input}
                    )
                    data = res.json()

                    if "error" in data:
                        answer = "❌ 오류: " + data["error"]
                    else:
                        answer = data["answer"]

                except Exception as e:
                    answer = f"서버 연결 실패: {str(e)}"

            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.rerun()

# 오른쪽: 인기 질문 패널 (마찬가지로 container(key=...)로 진짜 하나의 카드)
with faq_col:
    with st.container(key="faq_panel"):
        st.markdown(
            '<div class="panel-title">💗 인기 질문 예시</div><div class="panel-spacer"></div>',
            unsafe_allow_html=True,
        )

        questions = [
            "☔ 비 오는 날 데이트 코스 추천",
            "🌃 서울 야경 데이트 장소 알려줘",
            "🍽️ 기념일에 가기 좋은 레스토랑",
            "📸 커플 사진 잘 나오는 장소"
        ]

        for q in questions:
            if st.button(q, key=q):
                st.session_state.quick = q