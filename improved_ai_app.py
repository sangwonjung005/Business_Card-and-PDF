import streamlit as st
from PIL import Image
import pytesseract
import requests
import json
import time

# 페이지 설정
st.set_page_config(
    page_title="명함 & AI 도우미",
    page_icon="💼",
    layout="wide"
)

# 세션 상태 초기화
if "business_cards" not in st.session_state:
    st.session_state.business_cards = []
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# AI API 호출 함수
def call_ai_api(question: str) -> str:
    """AI API 호출"""
    try:
        # Hugging Face Inference API 사용
        API_URL = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
        
        headers = {
            "Authorization": f"Bearer {st.secrets.get('HUGGINGFACE_API_KEY', '')}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": question,
            "parameters": {
                "max_length": 100,
                "temperature": 0.7
            }
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get('generated_text', '답변을 생성할 수 없습니다.')
            else:
                return str(result)
        else:
            return f"API 오류: {response.status_code}"
            
    except Exception as e:
        return f"오류 발생: {str(e)}"

# 명함 정보 추출 함수
def extract_business_card_info(image):
    """명함에서 정보 추출"""
    try:
        # 이미지를 그레이스케일로 변환
        gray_image = image.convert('L')
        
        # OCR 실행
        text = pytesseract.image_to_string(gray_image, lang='kor+eng')
        
        # 텍스트를 줄별로 분리하고 빈 줄 제거
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # 기본 정보 구조
        info = {
            "name": "이름을 찾을 수 없음",
            "company": "회사명을 찾을 수 없음", 
            "phone": "전화번호를 찾을 수 없음",
            "email": "이메일을 찾을 수 없음",
            "raw_text": text
        }
        
        # 각 줄 분석
        for line in lines:
            # 이메일 찾기 (@ 포함)
            if '@' in line and '.' in line:
                info["email"] = line
                
            # 전화번호 찾기 (숫자 8개 이상)
            elif sum(c.isdigit() for c in line) >= 8:
                info["phone"] = line
                
            # 회사명 찾기 (대문자 포함, 3자 이상)
            elif any(c.isupper() for c in line) and len(line) >= 3:
                if info["company"] == "회사명을 찾을 수 없음":
                    info["company"] = line
                    
            # 이름 찾기 (한글/영문, 2-10자, 숫자 없음)
            elif 2 <= len(line) <= 10 and not any(c.isdigit() for c in line):
                if info["name"] == "이름을 찾을 수 없음":
                    info["name"] = line
        
        return info
        
    except Exception as e:
        st.error(f"추출 중 오류: {str(e)}")
        return {
            "name": "오류 발생",
            "company": "오류 발생",
            "phone": "오류 발생", 
            "email": "오류 발생",
            "raw_text": "텍스트 추출 실패"
        }

# 메인 UI
st.title("💼 명함 & AI 도우미")
st.markdown("**명함 OCR과 AI 채팅**")

# 탭 생성
tab1, tab2, tab3, tab4 = st.tabs(["📇 명함 OCR", "💬 명함 질문", "🤖 AI 채팅", "📊 대화 기록"])

with tab1:
    st.header("📇 명함 OCR")
    st.write("명함 이미지를 업로드하면 정보를 추출합니다.")
    
    uploaded_image = st.file_uploader("명함 이미지 업로드", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_image is not None:
        image = Image.open(uploaded_image)
        st.image(image, caption="업로드된 명함", use_column_width=True)
        
        if st.button("🔍 정보 추출", type="primary"):
            with st.spinner("명함 정보를 추출하고 있습니다..."):
                card_info = extract_business_card_info(image)
                
                # 세션에 저장
                card_info["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.business_cards.append(card_info)
                
                st.success("✅ 정보 추출 완료!")
                
                # 결과 표시
                st.subheader("📋 추출된 정보")
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**이름:** {card_info['name']}")
                    st.info(f"**회사:** {card_info['company']}")
                with col2:
                    st.info(f"**전화:** {card_info['phone']}")
                    st.info(f"**이메일:** {card_info['email']}")
                
                with st.expander("원본 텍스트"):
                    st.text(card_info['raw_text'])

with tab2:
    st.header("💬 명함에 대해 질문하기")
    
    if st.session_state.business_cards:
        selected_card_index = st.selectbox(
            "질문할 명함을 선택하세요:",
            range(len(st.session_state.business_cards)),
            format_func=lambda x: f"{st.session_state.business_cards[x].get('name', 'Unknown')} - {st.session_state.business_cards[x].get('company', 'Unknown')}"
        )
        
        if selected_card_index is not None:
            selected_card = st.session_state.business_cards[selected_card_index]
            
            card_question = st.text_input(
                "명함에 대해 질문하세요:",
                placeholder="예: 연락처는? 이름은? 회사는?"
            )
            
            if st.button("🤖 답변 생성", key="card_qa") and card_question:
                with st.spinner("답변을 생성하고 있습니다..."):
                    # 명함 정보를 포함한 답변
                    if "연락처" in card_question or "전화" in card_question:
                        answer = f"연락처 정보입니다:\n- 전화: {selected_card['phone']}\n- 이메일: {selected_card['email']}"
                    elif "이름" in card_question:
                        answer = f"이름은 {selected_card['name']}입니다."
                    elif "회사" in card_question:
                        answer = f"회사는 {selected_card['company']}입니다."
                    else:
                        answer = call_ai_api(card_question)
                    
                    # 대화 기록 저장
                    conversation_entry = {
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "question": card_question,
                        "answer": answer,
                        "type": "명함 질문"
                    }
                    st.session_state.conversation_history.append(conversation_entry)
                    
                    st.subheader("🤖 답변")
                    st.write(answer)
    else:
        st.info("먼저 명함을 업로드해주세요.")

with tab3:
    st.header("🤖 AI 채팅")
    chat_question = st.text_input("질문을 입력하세요:", placeholder="무엇이든 물어보세요...")
    
    if st.button("🤖 답변 생성", key="chat_qa") and chat_question:
        with st.spinner("답변을 생성하고 있습니다..."):
            answer = call_ai_api(chat_question)
            
            # 대화 기록 저장
            conversation_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "question": chat_question,
                "answer": answer,
                "type": "일반 채팅"
            }
            st.session_state.conversation_history.append(conversation_entry)
            
            st.subheader("🤖 답변")
            st.write(answer)

with tab4:
    st.header("📊 대화 기록")
    if st.session_state.conversation_history:
        for i, entry in enumerate(reversed(st.session_state.conversation_history)):
            with st.expander(f"{entry['type']} - {entry['question'][:30]}..."):
                st.write(f"**질문:** {entry['question']}")
                st.write(f"**답변:** {entry['answer']}")
                st.write(f"**시간:** {entry['timestamp']}")
    else:
        st.info("아직 대화 기록이 없습니다.")

# 초기화 버튼
if st.button("🗑️ 모든 데이터 초기화"):
    st.session_state.business_cards = []
    st.session_state.conversation_history = []
    st.success("초기화 완료!")
    st.rerun()

# 사이드바
with st.sidebar:
    st.header("📊 통계")
    st.write(f"저장된 명함: {len(st.session_state.business_cards)}")
    st.write(f"대화 수: {len(st.session_state.conversation_history)}")
    
    st.markdown("---")
    st.header("💡 사용법")
    st.write("""
    1. **명함 이미지 업로드**
    2. **정보 추출 버튼 클릭**
    3. **명함에 대해 질문하기**
    4. **AI와 자유롭게 대화하기**
    """)
    
    st.markdown("---")
    st.header("🔧 기능")
    st.write("""
    ✅ **명함 OCR**: 텍스트 추출
    ✅ **명함 질문**: 연락처, 이름, 회사 등
    ✅ **AI 채팅**: 일반적인 대화
    ✅ **대화 기록**: 모든 대화 저장
    """)
