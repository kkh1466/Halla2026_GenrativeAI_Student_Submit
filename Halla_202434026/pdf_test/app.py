import os
import streamlit as st

from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

from langchain_core.prompts import ChatPromptTemplate

from langchain_core.prompts import ChatPromptTemplate

# 1. API 키 설정 (구글모델 사용)
os.environ["GOOGLE_API_KEY"] = "YOUR_API_KEY"
# 2. PDF 파일 로드 및 벡터DB 구축 (딱 한 번만 실행되게 설정)
@st.cache_resource
def setup_rag():
    # PDF 폴더 경로 
    loader = PyPDFDirectoryLoader("D:\\바탕화면\\GitCode\\pdf_test")
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = text_splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
    vectorstore = FAISS.from_documents(documents=splits, embedding=embeddings)
    return vectorstore.as_retriever()

if "messages" not in st.session_state:
    st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


# 시스템 가동

st.set_page_config(
    page_title="PDF RAG 챗봇",
    page_icon="📄",
    layout="wide"
)

st.title("📄 PDF RAG 챗봇")
st.caption("PDF 여러 개를 읽고 질문에 답변합니다.")

with st.spinner('PDF 분석 중...'):
    retriever = setup_rag()

# 3. 잼띠와 연결
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
prompt = ChatPromptTemplate.from_template("""
제공된 문맥(Context)을 바탕으로 질문에 대답해 줍니다.
Context: {context}
Question: {input}
""")

document_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, document_chain)

# 4. 채팅 UI
query = st.chat_input("PDF에 대해 질문해보세요!")
if query:

    st.session_state.messages.append(
        {
            "role":"user",
            "content":query
        }
    )

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):

        with st.spinner("생각하는 중..."):

            response = rag_chain.invoke(
                {"input":query}
            )

            answer = response["answer"]

            st.markdown(answer)

            with st.expander("📚 참고한 문서"):

                shown=set()

                for doc in response["context"]:

                    filename=doc.metadata["source"].split("\\")[-1]

                    page=doc.metadata.get("page",0)+1

                    if (filename,page) not in shown:

                        shown.add((filename,page))

                        st.write(f"📄 {filename} ({page}페이지)")        
        
    st.session_state.messages.append(
        {
            "role":"assistant",
            "content":answer
        }
    )
    
    with st.sidebar:

        st.title("📄 PDF RAG")

    st.success("현재 상태")

    st.write("✅ PDF 로드 완료")

    st.write("✅ Gemini 연결")

    st.write("✅ FAISS 준비")

    st.divider()

    if st.button("🗑️ 대화 초기화"):

        st.session_state.messages=[]

        st.rerun()