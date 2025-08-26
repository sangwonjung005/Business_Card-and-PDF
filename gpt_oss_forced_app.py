import os
import streamlit as st
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
    page_title="GPT-OSS Only Business Card OCR & PDF Assistant",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 데이터 저장 파일 경로
DATA_DIR = "app_data"
BUSINESS_CARDS_FILE = os.path.join(DATA_DIR, "business_cards.json")
CONVERSATION_FILE = os.path.join(DATA_DIR, "conversation_history.json")

# 데이터 디렉토리 생성
os.makedirs(DATA_DIR, exist_ok=True)

def save_data_to_file(data, filename):
    """데이터를 JSON 파일로 저장"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"데이터 저장 실패: {str(e)}")
        return False

def load_data_from_file(filename, default_value):
    """JSON 파일에서 데이터 로드"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default_value
    except Exception as e:
        st.warning(f"데이터 로드 실패: {str(e)}")
        return default_value

# 세션 상태 초기화 (파일에서 로드)
if "business_cards" not in st.session_state:
    st.session_state.business_cards = load_data_from_file(BUSINESS_CARDS_FILE, [])
if "pdf_docs" not in st.session_state:
    st.session_state.pdf_docs = None
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = load_data_from_file(CONVERSATION_FILE, [])

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
    """AI API 호출 - 여러 모델 시도 (Gemma 포함)"""
    
    # 핵심 모델들 (GPT-OSS + Gemma + 기본)
    models = [
        # GPT-OSS 모델들 (우선순위)
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        # Gemma 모델들 (사용 가능한지 확인)
        "google/gemma-3-270m",
        "google/gemma-2b",
        "google/gemma-7b",
        # 기본 안정 모델
        "microsoft/DialoGPT-medium"
    ]
    
    for model in models:
        try:
            st.write(f"🔄 Trying {model}...")
            
            # Hugging Face API 시도
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
            elif "gemma" in model:
                # Gemma 모델용 프롬프트 형식
                payload = {
                    "inputs": f"<start_of_turn>user\n{prompt}<end_of_turn>\n<start_of_turn>model\n",
                    "parameters": {
                        "max_new_tokens": 500,
                        "temperature": 0.3,
                        "do_sample": True,
                        "top_p": 0.9
                    }
                }
            elif "dialo" in model.lower():
                # DialoGPT 모델용 프롬프트 형식
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 300,
                        "temperature": 0.7,
                        "do_sample": True,
                        "pad_token_id": 50256
                    }
                }
            else:
                # 일반 GPT 모델들
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
                    # Gemma 특별 처리
                    if "gemma" in model:
                        # Gemma 응답에서 모델 부분만 추출
                        if "<start_of_turn>model\n" in generated_text:
                            generated_text = generated_text.split("<start_of_turn>model\n")[-1]
                        if "<end_of_turn>" in generated_text:
                            generated_text = generated_text.split("<end_of_turn>")[0]
                    st.success(f"✅ {model} 성공!")
                    return generated_text
                else:
                    st.warning(f"⚠️ {model}: 응답 형식 오류")
            else:
                st.warning(f"⚠️ {model}: HTTP {response.status_code}")
                
        except Exception as e:
            st.warning(f"⚠️ {model}: {str(e)}")
            continue
    
    # Hugging Face 실패시 Ollama 시도 (선택사항)
    st.info("🔄 Hugging Face 실패. Ollama Gemma 시도...")
    
    ollama_models = ["gemma3:270m", "gemma2:2b", "gemma2:7b"]
    
    for ollama_model in ollama_models:
        try:
            st.write(f"🔄 Trying Ollama {ollama_model}...")
            
            # Ollama API 호출
            ollama_url = "http://localhost:11434/api/generate"
            ollama_payload = {
                "model": ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 500
                }
            }
            
            response = requests.post(ollama_url, json=ollama_payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '')
                if generated_text:
                    st.success(f"✅ Ollama {ollama_model} 성공!")
                    return generated_text
                else:
                    st.warning(f"⚠️ Ollama {ollama_model}: 빈 응답")
            else:
                st.warning(f"⚠️ Ollama {ollama_model}: HTTP {response.status_code}")
                
        except Exception as e:
            st.warning(f"⚠️ Ollama {ollama_model}: {str(e)}")
            continue
    
    # 모든 모델 실패시 기본 응답
    st.error("❌ 모든 모델 실패.")
    return "죄송합니다. 현재 AI 모델들을 사용할 수 없습니다. 잠시 후 다시 시도해주세요."

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
st.title("💼 AI Business Card OCR & PDF Assistant")
st.markdown("**GPT-OSS + Gemma + 오픈소스 AI** - 명함 OCR과 PDF 질의응답 시스템")

# 기능 선택
selected_function = st.selectbox(
    "기능을 선택하세요:",
    ["📇 명함 OCR", "📄 PDF RAG", "🤖 AI 채팅", "💬 대화 기록"],
    index=0
)

if selected_function == "📇 명함 OCR":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("📇 명함 OCR (AI)")
    st.write("명함 이미지를 업로드하면 GPT-OSS, Gemma 또는 기타 AI가 정보를 추출합니다.")
    
    uploaded_image = st.file_uploader(
        "명함 이미지 업로드",
        type=['png', 'jpg', 'jpeg'],
        help="명함 사진을 업로드하세요"
    )
    
    if uploaded_image is not None:
        image = Image.open(uploaded_image)
        st.image(image, caption="업로드된 명함", use_column_width=True)
        
        if st.button("🔍 AI로 명함 정보 추출", type="primary"):
            with st.spinner("AI가 명함 정보를 추출하고 있습니다..."):
                card_info = extract_business_card_info(image)
                
                if card_info and "error" not in card_info:
                    # 명함 정보를 세션에 저장
                    card_info["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.business_cards.append(card_info)
                    
                    # 파일에 영구 저장
                    save_data_to_file(st.session_state.business_cards, BUSINESS_CARDS_FILE)
                    
                    # 결과 표시
                    st.markdown('<div class="business-card">', unsafe_allow_html=True)
                    st.subheader("📋 AI 추출 결과")
                    
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
                    
                    st.success("✅ AI가 명함 정보를 성공적으로 추출했습니다!")
                else:
                    st.error("AI 명함 정보 추출에 실패했습니다.")
    
    # 명함에 대한 질문 기능
    if st.session_state.business_cards:
        st.subheader("💬 명함에 대해 AI에게 질문하기")
        st.write("추출된 명함 정보에 대해 질문하세요.")
        
        # 명함 선택
        selected_card_index = st.selectbox(
            "질문할 명함을 선택하세요:",
            range(len(st.session_state.business_cards)),
            format_func=lambda x: f"{st.session_state.business_cards[x].get('name', 'Unknown')} - {st.session_state.business_cards[x].get('company', 'Unknown')}"
        )
        
        if selected_card_index is not None:
            selected_card = st.session_state.business_cards[selected_card_index]
            
            # 선택된 명함 정보 표시
            with st.expander("선택된 명함 정보"):
                st.json(selected_card)
            
            # 질문 입력
            card_question = st.text_input(
                "명함에 대해 질문하세요:",
                placeholder="예: 이 사람의 연락처는? 회사 주소는? 직책은?",
                key="card_question"
            )
            
            if st.button("🤖 AI 답변 생성", type="primary", key="card_question_button") and card_question:
                with st.spinner("AI가 명함 정보를 바탕으로 답변을 생성하고 있습니다..."):
                    # 명함 정보를 컨텍스트로 사용
                    card_context = f"""
명함 정보:
이름: {selected_card.get('name', 'N/A')}
직책: {selected_card.get('title', 'N/A')}
회사: {selected_card.get('company', 'N/A')}
이메일: {selected_card.get('email', 'N/A')}
전화: {selected_card.get('phone', 'N/A')}
휴대폰: {selected_card.get('mobile', 'N/A')}
주소: {selected_card.get('address', 'N/A')}
웹사이트: {selected_card.get('website', 'N/A')}
부서: {selected_card.get('department', 'N/A')}
"""
                    
                    # AI 답변 생성
                    card_answer = generate_answer(card_question, card_context)
                    
                    # 대화 기록에 저장
                    conversation_entry = {
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "question": card_question,
                        "answer": card_answer,
                        "context": f"명함 정보: {selected_card.get('name', 'Unknown')}",
                        "type": "business_card_qa"
                    }
                    st.session_state.conversation_history.append(conversation_entry)
                    
                    # 파일에 영구 저장
                    save_data_to_file(st.session_state.conversation_history, CONVERSATION_FILE)
                    
                    # 답변 표시
                    st.markdown('<div class="business-card">', unsafe_allow_html=True)
                    st.subheader("🤖 AI 답변")
                    st.write(card_answer)
                    st.markdown('</div>', unsafe_allow_html=True)
    
    # 저장된 명함 목록
    if st.session_state.business_cards:
        st.subheader("📚 저장된 명함 목록")
        for i, card in enumerate(st.session_state.business_cards):
            with st.expander(f"명함 {i+1}: {card.get('name', 'Unknown')} - {card.get('company', 'Unknown')}"):
                st.json(card)
    st.markdown('</div>', unsafe_allow_html=True)

elif selected_function == "📄 PDF RAG":
    st.markdown('<div class="pdf-section">', unsafe_allow_html=True)
    st.header("📄 PDF RAG (AI)")
    st.write("PDF를 업로드하고 질문하면 GPT-OSS, Gemma 또는 기타 AI가 답변합니다.")
    
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
        st.subheader("💬 PDF에 대해 AI에게 질문하기")
        
        question = st.text_input(
            "질문을 입력하세요:",
            placeholder="PDF 내용에 대해 질문하세요..."
        )
        
        if st.button("🤖 AI 답변 생성", type="primary") and question:
            with st.spinner("AI가 답변을 생성하고 있습니다..."):
                # 컨텍스트 생성
                context = get_context(question, st.session_state.pdf_docs)
                
                # GPT-OSS 답변 생성
                answer = generate_answer(question, context)
                
                # 대화 기록에 저장
                conversation_entry = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "question": question,
                    "answer": answer,
                    "context": context[:200] + "..." if len(context) > 200 else context,
                    "type": "pdf_rag"
                }
                st.session_state.conversation_history.append(conversation_entry)
                
                # 파일에 영구 저장
                save_data_to_file(st.session_state.conversation_history, CONVERSATION_FILE)
                
                # 답변 표시
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("🤖 AI 답변")
                st.write(answer)
                
                if context:
                    with st.expander("📄 사용된 컨텍스트"):
                        st.text(context)
                
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("📄 PDF를 먼저 업로드해주세요.")
    st.markdown('</div>', unsafe_allow_html=True)

elif selected_function == "🤖 AI 채팅":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("🤖 AI 채팅")
    st.write("GPT-OSS, Gemma 또는 기타 AI와 자유롭게 대화하세요.")
    
    # 채팅 입력
    chat_question = st.text_input(
        "질문을 입력하세요:",
        placeholder="무엇이든 물어보세요...",
        key="chat_input"
    )
    
    if st.button("🤖 AI 답변 생성", type="primary", key="chat_button") and chat_question:
        with st.spinner("AI가 답변을 생성하고 있습니다..."):
            # AI 답변 생성
            chat_answer = call_gpt_oss_api(chat_question)
            
            # 대화 기록에 저장
            conversation_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "question": chat_question,
                "answer": chat_answer,
                "context": "일반 채팅",
                "type": "chat"
            }
            st.session_state.conversation_history.append(conversation_entry)
            
            # 파일에 영구 저장
            save_data_to_file(st.session_state.conversation_history, CONVERSATION_FILE)
            
            # 답변 표시
            st.markdown('<div class="business-card">', unsafe_allow_html=True)
            st.subheader("🤖 AI 답변")
            st.write(chat_answer)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # 채팅 예시
    st.subheader("💡 질문 예시")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("안녕하세요!", key="example1"):
            st.session_state.chat_input = "안녕하세요!"
            st.rerun()
        if st.button("오늘 날씨는?", key="example2"):
            st.session_state.chat_input = "오늘 날씨는 어떤가요?"
            st.rerun()
        if st.button("재미있는 이야기 해줘", key="example3"):
            st.session_state.chat_input = "재미있는 이야기나 농담을 해줘"
            st.rerun()
    
    with col2:
        if st.button("코딩 도움", key="example4"):
            st.session_state.chat_input = "Python으로 간단한 계산기 만드는 방법을 알려줘"
            st.rerun()
        if st.button("요리 레시피", key="example5"):
            st.session_state.chat_input = "김치찌개 만드는 방법을 알려줘"
            st.rerun()
        if st.button("여행 추천", key="example6"):
            st.session_state.chat_input = "한국에서 가볼 만한 여행지 추천해줘"
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

elif selected_function == "💬 대화 기록":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("💬 AI 대화 기록")
    
    if st.session_state.conversation_history:
        for i, entry in enumerate(reversed(st.session_state.conversation_history)):
            # 대화 타입에 따른 아이콘
            if entry.get('type') == 'chat':
                icon = "💬"
                title = f"채팅 {len(st.session_state.conversation_history) - i}"
            elif entry.get('type') == 'business_card_qa':
                icon = "📇"
                title = f"명함 질문 {len(st.session_state.conversation_history) - i}"
            else:
                icon = "📄"
                title = f"PDF 대화 {len(st.session_state.conversation_history) - i}"
            
            with st.expander(f"{icon} {title}: {entry['question'][:50]}..."):
                st.write(f"**질문:** {entry['question']}")
                st.write(f"**AI 답변:** {entry['answer']}")
                st.write(f"**시간:** {entry['timestamp']}")
                st.write(f"**타입:** {entry.get('type', 'PDF RAG')}")
                
                if entry.get('context') and entry.get('context') != "일반 채팅":
                    with st.expander("컨텍스트"):
                        st.text(entry['context'])
    else:
        st.info("아직 AI 대화 기록이 없습니다.")
    
    # 대화 기록 초기화
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ 대화 기록 초기화"):
            st.session_state.conversation_history = []
            # 파일에서도 삭제
            try:
                if os.path.exists(CONVERSATION_FILE):
                    os.remove(CONVERSATION_FILE)
                st.success("대화 기록이 완전히 삭제되었습니다!")
            except:
                st.warning("파일 삭제에 실패했습니다.")
            st.rerun()
    
    with col2:
        if st.button("🗑️ 명함 데이터 초기화"):
            st.session_state.business_cards = []
            # 파일에서도 삭제
            try:
                if os.path.exists(BUSINESS_CARDS_FILE):
                    os.remove(BUSINESS_CARDS_FILE)
                st.success("명함 데이터가 완전히 삭제되었습니다!")
            except:
                st.warning("파일 삭제에 실패했습니다.")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# 사이드바 통계
with st.sidebar:
    st.header("📊 AI 통계")
    
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
    st.metric("AI 대화 수", len(st.session_state.conversation_history))
    
    st.markdown("---")
    
    # 데이터 관리 정보
    st.header("💾 데이터 관리")
    st.info(f"""
    **📁 저장 위치:** `{DATA_DIR}/`
    - 명함 데이터: `business_cards.json`
    - 대화 기록: `conversation_history.json`
    
    **🔄 자동 저장:** 모든 데이터는 자동으로 파일에 저장됩니다.
    **📱 영구 보존:** 브라우저를 닫아도 데이터가 유지됩니다.
    """)
    
    st.markdown("---")
    
    # 기능 설명
    st.header("🔧 AI 기능")
    st.write("""
    **📇 명함 OCR:**
    - 명함 이미지 업로드
    - AI 정보 추출 (GPT-OSS, Gemma, DialoGPT)
    - 구조화된 데이터 저장
    
    **📄 PDF RAG:**
    - PDF 문서 업로드
    - 텍스트 청킹
    - AI 기반 질의응답
    
    **🤖 AI 채팅:**
    - 자유로운 AI 대화
    - 질문 예시 제공
    - 다양한 주제 대화
    
    **💬 대화 기록:**
    - AI 질문-답변 히스토리
    - 채팅/PDF 대화 구분
    - 메모리 관리
    """)
