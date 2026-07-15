"""
EPL 챗봇 - Streamlit 웹 UI (축구장 테마)
실행: streamlit run app.py
"""
import streamlit as st
import pandas as pd
from text_to_sql import answer_question

st.set_page_config(page_title="EPL 챗봇 ⚽", page_icon="⚽", layout="centered")

# ================= 축구장 테마 CSS =================
st.markdown("""
<style>
.stApp {
    background: repeating-linear-gradient(
        180deg,
        #2e7d32 0px,
        #2e7d32 60px,
        #388e3c 60px,
        #388e3c 120px
    );
}
.pitch-header {
    position: relative;
    background: transparent;
    border-top: 5px solid #ffffff;
    border-bottom: 5px solid #ffffff;
    padding: 90px 10px 100px 10px;
    margin: 30px -10px 40px -10px;
    text-align: center;
    overflow: hidden;
}
.pitch-header::before {
    content: "";
    position: absolute;
    top: 50%;
    left: 50%;
    width: 260px;
    height: 260px;
    border: 4px solid rgba(255,255,255,0.35);
    border-radius: 50%;
    transform: translate(-50%, -50%);
    z-index: 0;
}
.pitch-header::after {
    content: "";
    position: absolute;
    top: 50%;
    left: 50%;
    width: 8px;
    height: 8px;
    background: rgba(255,255,255,0.5);
    border-radius: 50%;
    transform: translate(-50%, -50%);
    z-index: 0;
}
.pitch-title {
    position: relative;
    z-index: 2;
    color: #ffffff;
    font-size: 2.2rem;
    font-weight: 800;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.4);
    margin: 0;
}
.pitch-caption {
    position: relative;
    z-index: 2;
    color: #e8f5e9;
    font-size: 1rem;
    margin-top: 8px;
}
[data-testid="stChatMessage"] {
    background-color: #ffffff !important;
    border-radius: 14px;
    padding: 12px 16px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.25);
    margin-bottom: 10px;
    max-height: none !important;
    overflow: visible !important;
}
[data-testid="stChatMessageContent"] {
    max-height: none !important;
    overflow: visible !important;
    mask-image: none !important;
    -webkit-mask-image: none !important;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] div {
    color: #1a1a1a !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    border-left: 6px solid #d32f2f;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    border-left: 6px solid #fbc02d;
}
[data-testid="stChatInput"] textarea {
    background-color: #ffffff !important;
    border: 2px solid #ffffff !important;
    border-radius: 10px !important;
    color: #1a1a1a !important;
    caret-color: #1a1a1a !important;
}
[data-testid="stExpander"] {
    background-color: #ffffff;
    border-radius: 10px;
    padding: 4px;
}
</style>
""", unsafe_allow_html=True)

# ================= 헤더 =================
st.markdown("""
<div class="pitch-header">
    <p class="pitch-title">⚽ EPL 데이터 챗봇</p>
    <p class="pitch-caption">경기 결과, 득점자, 어시스트, 득점 시간을 자연어로 물어보세요</p>
</div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

question = st.chat_input("예: 골 많이 넣은 선수 순서대로 보여줘")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("⚽ 데이터 조회 중..."):
            result = answer_question(question)

        if result["error"]:
            st.error(f"쿼리 실행 중 문제가 발생했습니다: {result['error']}")
            with st.expander("생성된 SQL 보기"):
                st.code(result["sql"], language="sql")
        else:
            st.write(result["answer"])

            if result["rows"]:
                df = pd.DataFrame(result["rows"], columns=result["columns"])
                numeric_cols = df.select_dtypes(include="number").columns.tolist()
                non_numeric_cols = [c for c in df.columns if c not in numeric_cols]

                # 레이블 컬럼(텍스트)과 값 컬럼(숫자)이 각각 따로 존재할 때만 차트 표시
                if numeric_cols and non_numeric_cols and len(df) >= 2:
                    label_col = non_numeric_cols[0]
                    value_col = numeric_cols[0]
                    try:
                        chart_df = df.set_index(label_col)[[value_col]].sort_values(
                            value_col, ascending=False
                        )
                        st.bar_chart(chart_df, color="#2e7d32")
                    except Exception:
                        pass  # 차트 생성 실패 시 조용히 넘어가고 텍스트 답변은 그대로 유지

            with st.expander("조회된 원본 데이터 / SQL 보기"):
                st.code(result["sql"], language="sql")
                if result["rows"]:
                    st.dataframe(df)

    st.session_state.messages.append(
        {"role": "assistant", "content": result["answer"] or "조회 실패"}
    )