import os
import streamlit as st
from PyPDF2 import PdfReader
import time
import requests
from PIL import Image
import pytesseract
import json

# 페이지 설정
st.set_page_config(
    page_title="AI Business Card & PDF Assistant",
    page_icon="💼",
    layout="wide"
)

# 데이터 저장
DATA_DIR = "app_data"
os.makedirs(DATA_DIR, exist_ok=True)

# 세션 상태 초기화
if "business_cards" not in st.session_state:
    st.session_state.business_cards = []
if "pdf_docs" not in st.session_state:
    st.session_state.pdf_docs = None
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# AI API 호출 함수 (깔끔하게)
def call_ai_api(prompt: str) -> str:
    """AI API 호출 - 깔끔하게 처리"""
    
    # 간단한 모델 리스트 (API 키 없이 작동하는 모델들)
    models = [
        "microsoft/DialoGPT-medium",
        "gpt2",
        "EleutherAI/gpt-neo-125M"
    ]
    
    for model in models:
        try:
            API_URL = f"https://api-inference.huggingface.co/models/{model}"
            headers = {"Content-Type": "application/json"}
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 300,
                    "temperature": 0.3,
                    "do_sample": True
                }
            }
            
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    generated_text = result[0].get('generated_text', '')
                    if prompt in generated_text:
                        generated_text = generated_text.replace(prompt, '').strip()
                    return generated_text
                    
        except Exception:
            continue
    
    # 모든 모델 실패시 간단한 메시지
    return "죄송합니다. 현재 AI 서비스를 사용할 수 없습니다. 잠시 후 다시 시도해주세요."

# 명함 정보 추출
def extract_business_card_info(image):
    try:
        gray_image = image.convert('L')
        text = pytesseract.image_to_string(gray_image, lang='kor+eng')
        
        # AI로 정보 구조화
        prompt = f"""
다음 명함 텍스트에서 정보를 추출하여 JSON 형식으로 반환하세요:

{text}

다음 형식으로 반환하세요:
{{
    "name": "이름",
    "title": "직책", 
    "company": "회사명",
    "email": "이메일",
    "phone": "전화번호",
    "mobile": "휴대폰",
    "address": "주소",
    "website": "웹사이트"
}}

정보가 없는 경우 null로 표시하세요.
"""
        
        response = call_ai_api(prompt)
        
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
        
        return {
            "name": "추출 실패",
            "title": None,
            "company": None,
            "email": None,
            "phone": None,
            "mobile": None,
            "address": None,
            "website": None,
            "raw_text": text
        }
        
    except Exception as e:
        return {"error": str(e)}

# PDF 읽기
def read_pdf(file) -> str:
    text = ""
    reader = PdfReader(file)
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

# 메인 UI
st.title("💼 AI Business Card & PDF Assistant")
st.markdown("**GPT-OSS + Gemma AI**")

# 1. 명함 OCR
st.header("📇 명함 OCR")
st.write("명함 이미지를 업로드하면 AI가 정보를 추출합니다.")

uploaded_image = st.file_uploader("명함 이미지 업로드", type=['png', 'jpg', 'jpeg'])

if uploaded_image is not None:
    image = Image.open(uploaded_image)
    st.image(image, caption="업로드된 명함", use_column_width=True)
    
    if st.button("🔍 AI로 명함 정보 추출", type="primary"):
        with st.spinner("AI가 명함 정보를 추출하고 있습니다..."):
            card_info = extract_business_card_info(image)
            
            if card_info and "error" not in card_info:
                card_info["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.business_cards.append(card_info)
                
                st.success("✅ AI가 명함 정보를 성공적으로 추출했습니다!")
                
                # 깔끔한 결과 표시 (이전 스타일)
                st.subheader("📋 추출된 명함 정보")
                
                col1, col2 = st.columns(2)
                with col1:
                    if card_info.get("name"):
                        st.info(f"**이름:** {card_info['name']}")
                    if card_info.get("title"):
                        st.info(f"**직책:** {card_info['title']}")
                    if card_info.get("company"):
                        st.info(f"**회사:** {card_info['company']}")
                with col2:
                    if card_info.get("email"):
                        st.info(f"**이메일:** {card_info['email']}")
                    if card_info.get("phone"):
                        st.info(f"**전화:** {card_info['phone']}")
                    if card_info.get("mobile"):
                        st.info(f"**휴대폰:** {card_info['mobile']}")
                
                if card_info.get("address"):
                    st.info(f"**주소:** {card_info['address']}")
                if card_info.get("website"):
                    st.info(f"**웹사이트:** {card_info['website']}")
            else:
                st.error("AI 명함 정보 추출에 실패했습니다.")

# 명함 질문 기능
if st.session_state.business_cards:
    st.subheader("💬 명함에 대해 질문하기")
    
    selected_card_index = st.selectbox(
        "질문할 명함을 선택하세요:",
        range(len(st.session_state.business_cards)),
        format_func=lambda x: f"{st.session_state.business_cards[x].get('name', 'Unknown')} - {st.session_state.business_cards[x].get('company', 'Unknown')}"
    )
    
    if selected_card_index is not None:
        selected_card = st.session_state.business_cards[selected_card_index]
        
        card_question = st.text_input(
            "명함에 대해 질문하세요:",
            placeholder="예: 이 사람의 연락처는? 회사 주소는?"
        )
        
        if st.button("🤖 AI 답변 생성", key="card_qa") and card_question:
            with st.spinner("AI가 답변을 생성하고 있습니다..."):
                card_context = f"""
명함 정보:
이름: {selected_card.get('name', 'N/A')}
직책: {selected_card.get('title', 'N/A')}
회사: {selected_card.get('company', 'N/A')}
이메일: {selected_card.get('email', 'N/A')}
전화: {selected_card.get('phone', 'N/A')}
휴대폰: {selected_card.get('mobile', 'N/A')}
주소: {selected_card.get('address', 'N/A')}
"""
                
                prompt = f"다음 정보를 참고하여 질문에 답변하세요.\n\n참고 정보:\n{card_context}\n\n질문: {card_question}\n\n답변:"
                answer = call_ai_api(prompt)
                
                # 대화 기록 저장
                conversation_entry = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "question": card_question,
                    "answer": answer,
                    "type": "명함 질문"
                }
                st.session_state.conversation_history.append(conversation_entry)
                
                st.subheader("🤖 AI 답변")
                st.write(answer)

# 저장된 명함 목록 (깔끔하게)
if st.session_state.business_cards:
    st.subheader("📚 저장된 명함 목록")
    for i, card in enumerate(st.session_state.business_cards):
        with st.expander(f"명함 {i+1}: {card.get('name', 'Unknown')} - {card.get('company', 'Unknown')}"):
            # 깔끔한 카드 형태로 표시
            col1, col2 = st.columns(2)
            with col1:
                if card.get("name"):
                    st.write(f"**이름:** {card['name']}")
                if card.get("title"):
                    st.write(f"**직책:** {card['title']}")
                if card.get("company"):
                    st.write(f"**회사:** {card['company']}")
            with col2:
                if card.get("email"):
                    st.write(f"**이메일:** {card['email']}")
                if card.get("phone"):
                    st.write(f"**전화:** {card['phone']}")
                if card.get("mobile"):
                    st.write(f"**휴대폰:** {card['mobile']}")
            
            if card.get("address"):
                st.write(f"**주소:** {card['address']}")
            if card.get("website"):
                st.write(f"**웹사이트:** {card['website']}")
            
            st.caption(f"추출 시간: {card.get('timestamp', 'N/A')}")

st.markdown("---")

# 2. PDF RAG
st.header("📄 PDF RAG")
st.write("PDF를 업로드하고 질문하면 AI가 답변합니다.")

uploaded_pdf = st.file_uploader("PDF 파일 업로드", type=['pdf'])

if uploaded_pdf is not None:
    with st.spinner("PDF를 처리하고 있습니다..."):
        pdf_text = read_pdf(uploaded_pdf)
        if pdf_text:
            st.session_state.pdf_docs = pdf_text
            st.success(f"✅ PDF 처리 완료! {len(pdf_text)}자 텍스트 추출")
            
            with st.expander("PDF 내용 미리보기"):
                st.text(pdf_text[:1000] + "...")

if st.session_state.pdf_docs:
    st.subheader("💬 PDF에 대해 질문하기")
    
    pdf_question = st.text_input(
        "질문을 입력하세요:",
        placeholder="PDF 내용에 대해 질문하세요...",
        key="pdf_question"
    )
    
    if st.button("🤖 AI 답변 생성", key="pdf_qa") and pdf_question:
        with st.spinner("AI가 답변을 생성하고 있습니다..."):
            prompt = f"다음 정보를 참고하여 질문에 답변하세요.\n\n참고 정보:\n{st.session_state.pdf_docs[:2000]}...\n\n질문: {pdf_question}\n\n답변:"
            answer = call_ai_api(prompt)
            
            # 대화 기록 저장
            conversation_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "question": pdf_question,
                "answer": answer,
                "type": "PDF 질문"
            }
            st.session_state.conversation_history.append(conversation_entry)
            
            st.subheader("🤖 AI 답변")
            st.write(answer)

st.markdown("---")

# 3. AI 채팅
st.header("🤖 AI 채팅")
st.write("AI와 자유롭게 대화하세요.")

chat_question = st.text_input(
    "질문을 입력하세요:",
    placeholder="무엇이든 물어보세요...",
    key="chat_question"
)

if st.button("🤖 AI 답변 생성", key="chat_qa") and chat_question:
    with st.spinner("AI가 답변을 생성하고 있습니다..."):
        answer = call_ai_api(chat_question)
        
        # 대화 기록 저장
        conversation_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "question": chat_question,
            "answer": answer,
            "type": "일반 채팅"
        }
        st.session_state.conversation_history.append(conversation_entry)
        
        st.subheader("🤖 AI 답변")
        st.write(answer)

# 질문 예시
st.subheader("💡 질문 예시")
col1, col2 = st.columns(2)
with col1:
    if st.button("안녕하세요!", key="ex1"):
        st.session_state.chat_question = "안녕하세요!"
        st.rerun()
    if st.button("재미있는 이야기", key="ex2"):
        st.session_state.chat_question = "재미있는 이야기를 해줘"
        st.rerun()
with col2:
    if st.button("코딩 도움", key="ex3"):
        st.session_state.chat_question = "Python으로 간단한 계산기 만드는 방법을 알려줘"
        st.rerun()
    if st.button("요리 레시피", key="ex4"):
        st.session_state.chat_question = "김치찌개 만드는 방법을 알려줘"
        st.rerun()

st.markdown("---")

# 4. 대화 기록
st.header("💬 대화 기록")

if st.session_state.conversation_history:
    for i, entry in enumerate(reversed(st.session_state.conversation_history)):
        with st.expander(f"{entry['type']} - {entry['question'][:50]}..."):
            st.write(f"**질문:** {entry['question']}")
            st.write(f"**AI 답변:** {entry['answer']}")
            st.write(f"**시간:** {entry['timestamp']}")
else:
    st.info("아직 대화 기록이 없습니다.")

# 초기화 버튼
col1, col2 = st.columns(2)
with col1:
    if st.button("🗑️ 대화 기록 초기화"):
        st.session_state.conversation_history = []
        st.success("대화 기록이 삭제되었습니다!")
        st.rerun()
with col2:
    if st.button("🗑️ 명함 데이터 초기화"):
        st.session_state.business_cards = []
        st.success("명함 데이터가 삭제되었습니다!")
        st.rerun()

# 사이드바 통계
with st.sidebar:
    st.header("📊 통계")
    st.metric("저장된 명함", len(st.session_state.business_cards))
    st.metric("대화 수", len(st.session_state.conversation_history))
    
    st.markdown("---")
    st.header("🔧 기능")
    st.write("""
    **📇 명함 OCR:**
    - 명함 이미지 업로드
    - AI 정보 추출
    - 명함 질문 기능
    
    **📄 PDF RAG:**
    - PDF 업로드
    - AI 질의응답
    
    **🤖 AI 채팅:**
    - 자유로운 대화
    - 질문 예시
    
    **💬 대화 기록:**
    - 모든 대화 저장
    - 타입별 구분
    """)
