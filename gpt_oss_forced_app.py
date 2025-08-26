import os
import streamlit as st
from openai import OpenAI
from PyPDF2 import PdfReader
import numpy as np
import time
import re
import requests
from PIL import Image
import pytesseract
import json
from typing import Dict, List, Optional
import base64
from io import BytesIO

# 페이지 설정
st.set_page_config(
    page_title="GPT-OSS Business Card OCR & PDF Assistant",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# OpenAI API 키 설정 (fallback용)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    key_candidates = [
        os.path.join(os.path.dirname(__file__), "nocommit_key.txt"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "nocommit_key.txt"),
    ]
    for cand in key_candidates:
        if os.path.isfile(cand):
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    OPENAI_API_KEY = f.read().strip()
                break
            except Exception:
                pass

# OpenAI 클라이언트 (fallback용)
client = OpenAI(api_key=OPENAI_API_KEY)

# 세션 상태 초기화
if "business_cards" not in st.session_state:
    st.session_state.business_cards = []
if "pdf_docs" not in st.session_state:
    st.session_state.pdf_docs = None
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# CSS 스타일
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #ffffff;
    }
    
    .card {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .business-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        color: white;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    
    .pdf-section {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        color: #333;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 10px 25px;
        font-weight: bold;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    }
</style>
""", unsafe_allow_html=True)

def call_gpt_oss_api(prompt: str) -> str:
    """GPT-OSS API 호출 - 여러 모델 시도"""
    
    # 다양한 GPT-OSS 모델들
    gpt_oss_models = [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "microsoft/DialoGPT-medium",
        "gpt2",
        "EleutherAI/gpt-neo-125M",
        "microsoft/DialoGPT-small"
    ]
    
    for model in gpt_oss_models:
        try:
            st.write(f"🔄 Trying {model}...")
            
            API_URL = f"https://api-inference.huggingface.co/models/{model}"
            headers = {"Content-Type": "application/json"}
            
            # 모델별 다른 프롬프트 형식
            if "gpt-oss" in model:
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 500,
                        "temperature": 0.3,
                        "do_sample": True
                    }
                }
            else:
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 200,
                        "temperature": 0.7,
                        "do_sample": True
                    }
                }
            
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    generated_text = result[0].get('generated_text', '')
                    # 프롬프트 제거
                    if prompt in generated_text:
                        generated_text = generated_text.replace(prompt, '').strip()
                    st.success(f"✅ {model} 성공!")
                    return generated_text
                else:
                    st.warning(f"⚠️ {model}: 응답 형식 오류")
            else:
                st.warning(f"⚠️ {model}: HTTP {response.status_code}")
                
        except Exception as e:
            st.warning(f"⚠️ {model}: {str(e)}")
            continue
    
    # 모든 GPT-OSS 모델 실패시 OpenAI fallback
    st.error("❌ 모든 GPT-OSS 모델 실패. OpenAI fallback 사용...")
    try:
        if client:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        else:
            return "모든 API 호출에 실패했습니다."
    except Exception as e:
        return f"Fallback도 실패: {str(e)}"

def extract_business_card_info(image):
    """명함 이미지에서 정보 추출"""
    try:
        # 이미지 전처리 (PIL 사용)
        gray_image = image.convert('L')
        
        # 이미지 크기 조정
        width, height = gray_image.size
        if width > 1200:
            ratio = 1200 / width
            new_width = 1200
            new_height = int(height * ratio)
            gray_image = gray_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # OCR 실행
        text = pytesseract.image_to_string(gray_image, lang='kor+eng')
        
        # GPT-OSS를 사용하여 정보 구조화
        structured_info = structure_business_card_info(text)
        
        return structured_info
        
    except Exception as e:
        st.error(f"명함 정보 추출 중 오류: {str(e)}")
        return None

def structure_business_card_info(raw_text):
    """GPT-OSS를 사용하여 명함 정보를 구조화"""
    try:
        prompt = f"""
다음 명함 텍스트에서 정보를 추출하여 JSON 형식으로 반환하세요:

{raw_text}

다음 형식으로 반환하세요:
{{
    "name": "이름",
    "title": "직책",
    "company": "회사명",
    "email": "이메일",
    "phone": "전화번호",
    "mobile": "휴대폰",
    "address": "주소",
    "website": "웹사이트",
    "department": "부서"
}}

정보가 없는 경우 null로 표시하세요.
"""
        
        # GPT-OSS API 호출
        response = call_gpt_oss_api(prompt)
        
        # JSON 파싱 시도
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
        
        # JSON 파싱 실패시 기본 구조 반환
        return {
            "name": "추출 실패",
            "title": None,
            "company": None,
            "email": None,
            "phone": None,
            "mobile": None,
            "address": None,
            "website": None,
            "department": None,
            "raw_text": raw_text,
            "gpt_oss_response": response
        }
        
    except Exception as e:
        return {"error": str(e), "raw_text": raw_text}

def read_pdf(file) -> str:
    """PDF 읽기"""
    text = ""
    reader = PdfReader(file)
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def chunk_text(text: str, chunk_size: int = 200, overlap: int = 50):
    """텍스트 청킹"""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        chunk = " ".join(words[start : start + chunk_size])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def get_context(question: str, docs: list) -> str:
    """컨텍스트 생성"""
    if not docs:
        return ""
    
    # 간단한 키워드 매칭
    question_words = set(question.lower().split())
    best_chunks = []
    
    for i, doc in enumerate(docs[:5]):
        doc_words = set(doc.lower().split())
        overlap = len(question_words.intersection(doc_words))
        if overlap > 0:
            best_chunks.append(doc)
    
    return "\n\n".join(best_chunks[:3]) if best_chunks else docs[0] if docs else ""

def generate_answer(question: str, context: str) -> str:
    """GPT-OSS를 사용한 답변 생성"""
    try:
        if context:
            prompt = f"""다음 정보를 참고하여 질문에 답변하세요.

참고 정보:
{context}

질문: {question}

답변:"""
        else:
            prompt = question
        
        response = call_gpt_oss_api(prompt)
        return response
        
    except Exception as e:
        return f"답변 생성 중 오류: {str(e)}"

# 메인 UI
st.title("💼 GPT-OSS Business Card OCR & PDF Assistant")
st.markdown("**GPT-OSS 강제 사용** - 명함 OCR과 PDF 질의응답 시스템")

# 탭 생성
tab1, tab2, tab3 = st.tabs(["📇 명함 OCR", "📄 PDF RAG", "💬 대화 기록"])

with tab1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("📇 명함 OCR (GPT-OSS)")
    st.write("명함 이미지를 업로드하면 GPT-OSS가 정보를 추출합니다.")
    
    uploaded_image = st.file_uploader(
        "명함 이미지 업로드",
        type=['png', 'jpg', 'jpeg'],
        help="명함 사진을 업로드하세요"
    )
    
    if uploaded_image is not None:
        image = Image.open(uploaded_image)
        st.image(image, caption="업로드된 명함", use_column_width=True)
        
        if st.button("🔍 GPT-OSS로 명함 정보 추출", type="primary"):
            with st.spinner("GPT-OSS가 명함 정보를 추출하고 있습니다..."):
                card_info = extract_business_card_info(image)
                
                if card_info and "error" not in card_info:
                    # 명함 정보를 세션에 저장
                    card_info["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.business_cards.append(card_info)
                    
                    # 결과 표시
                    st.markdown('<div class="business-card">', unsafe_allow_html=True)
                    st.subheader("📋 GPT-OSS 추출 결과")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if card_info.get("name"):
                            st.write(f"**이름:** {card_info['name']}")
                        if card_info.get("title"):
                            st.write(f"**직책:** {card_info['title']}")
                        if card_info.get("company"):
                            st.write(f"**회사:** {card_info['company']}")
                        if card_info.get("department"):
                            st.write(f"**부서:** {card_info['department']}")
                    
                    with col2:
                        if card_info.get("email"):
                            st.write(f"**이메일:** {card_info['email']}")
                        if card_info.get("phone"):
                            st.write(f"**전화:** {card_info['phone']}")
                        if card_info.get("mobile"):
                            st.write(f"**휴대폰:** {card_info['mobile']}")
                        if card_info.get("website"):
                            st.write(f"**웹사이트:** {card_info['website']}")
                    
                    if card_info.get("address"):
                        st.write(f"**주소:** {card_info['address']}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.success("✅ GPT-OSS가 명함 정보를 성공적으로 추출했습니다!")
                else:
                    st.error("GPT-OSS 명함 정보 추출에 실패했습니다.")
    
    # 저장된 명함 목록
    if st.session_state.business_cards:
        st.subheader("📚 저장된 명함 목록")
        for i, card in enumerate(st.session_state.business_cards):
            with st.expander(f"명함 {i+1}: {card.get('name', 'Unknown')} - {card.get('company', 'Unknown')}"):
                st.json(card)
    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="pdf-section">', unsafe_allow_html=True)
    st.header("📄 PDF RAG (GPT-OSS)")
    st.write("PDF를 업로드하고 질문하면 GPT-OSS가 답변합니다.")
    
    uploaded_pdf = st.file_uploader(
        "PDF 파일 업로드",
        type=['pdf'],
        help="PDF 파일을 업로드하세요"
    )
    
    if uploaded_pdf is not None:
        with st.spinner("PDF를 처리하고 있습니다..."):
            pdf_text = read_pdf(uploaded_pdf)
            if pdf_text:
                chunks = chunk_text(pdf_text)
                st.session_state.pdf_docs = chunks
                st.success(f"✅ PDF 처리 완료! {len(chunks)}개 청크 생성")
                
                # PDF 내용 미리보기
                with st.expander("📖 PDF 내용 미리보기"):
                    st.text_area("PDF 내용", pdf_text[:1000] + "...", height=200, disabled=True)
    
    # 질문 입력
    if st.session_state.pdf_docs:
        st.subheader("💬 PDF에 대해 GPT-OSS에게 질문하기")
        
        question = st.text_input(
            "질문을 입력하세요:",
            placeholder="PDF 내용에 대해 질문하세요..."
        )
        
        if st.button("🤖 GPT-OSS 답변 생성", type="primary") and question:
            with st.spinner("GPT-OSS가 답변을 생성하고 있습니다..."):
                # 컨텍스트 생성
                context = get_context(question, st.session_state.pdf_docs)
                
                # GPT-OSS 답변 생성
                answer = generate_answer(question, context)
                
                # 대화 기록에 저장
                conversation_entry = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "question": question,
                    "answer": answer,
                    "context": context[:200] + "..." if len(context) > 200 else context
                }
                st.session_state.conversation_history.append(conversation_entry)
                
                # 답변 표시
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("🤖 GPT-OSS 답변")
                st.write(answer)
                
                if context:
                    with st.expander("📄 사용된 컨텍스트"):
                        st.text(context)
                
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("📄 PDF를 먼저 업로드해주세요.")
    st.markdown('</div>', unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("💬 GPT-OSS 대화 기록")
    
    if st.session_state.conversation_history:
        for i, entry in enumerate(reversed(st.session_state.conversation_history)):
            with st.expander(f"대화 {len(st.session_state.conversation_history) - i}: {entry['question'][:50]}..."):
                st.write(f"**질문:** {entry['question']}")
                st.write(f"**GPT-OSS 답변:** {entry['answer']}")
                st.write(f"**시간:** {entry['timestamp']}")
                
                if entry.get('context'):
                    with st.expander("컨텍스트"):
                        st.text(entry['context'])
    else:
        st.info("아직 GPT-OSS 대화 기록이 없습니다.")
    
    # 대화 기록 초기화
    if st.button("🗑️ 대화 기록 초기화"):
        st.session_state.conversation_history = []
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# 사이드바 통계
with st.sidebar:
    st.header("📊 GPT-OSS 통계")
    
    # 명함 통계
    st.subheader("📇 명함")
    st.metric("저장된 명함", len(st.session_state.business_cards))
    
    # PDF 통계
    st.subheader("📄 PDF")
    if st.session_state.pdf_docs:
        st.metric("청크 수", len(st.session_state.pdf_docs))
    else:
        st.metric("청크 수", 0)
    
    # 대화 통계
    st.subheader("💬 대화")
    st.metric("GPT-OSS 대화 수", len(st.session_state.conversation_history))
    
    st.markdown("---")
    
    # 기능 설명
    st.header("🔧 GPT-OSS 기능")
    st.write("""
    **📇 명함 OCR:**
    - 명함 이미지 업로드
    - GPT-OSS 정보 추출
    - 구조화된 데이터 저장
    
    **📄 PDF RAG:**
    - PDF 문서 업로드
    - 텍스트 청킹
    - GPT-OSS 기반 질의응답
    
    **💬 대화 기록:**
    - GPT-OSS 질문-답변 히스토리
    - 컨텍스트 추적
    - 메모리 관리
    """)
