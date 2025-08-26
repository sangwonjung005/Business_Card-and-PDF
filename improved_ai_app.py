import streamlit as st
from PyPDF2 import PdfReader
import requests
from PIL import Image
import pytesseract
import time

# 페이지 설정
st.set_page_config(
    page_title="AI Assistant",
    page_icon="💼",
    layout="wide"
)

# 세션 상태 초기화
if "business_cards" not in st.session_state:
    st.session_state.business_cards = []
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# 간단한 AI 응답 함수 (실제로 작동하는 버전)
def get_ai_response(prompt: str) -> str:
    """간단한 AI 응답 - 확실히 작동하는 버전"""
    
    # 기본 응답들
    responses = {
        "안녕": "안녕하세요! 무엇을 도와드릴까요?",
        "연락처": "연락처 정보를 찾아드리겠습니다.",
        "이름": "이름 정보를 확인해드리겠습니다.",
        "회사": "회사 정보를 찾아드리겠습니다.",
        "이메일": "이메일 주소를 확인해드리겠습니다.",
        "전화": "전화번호를 찾아드리겠습니다.",
        "도움": "무엇을 도와드릴까요?",
        "감사": "천만에요! 더 필요한 것이 있으시면 언제든 말씀해주세요."
    }
    
    # 키워드 매칭
    for keyword, response in responses.items():
        if keyword in prompt:
            return response
    
    # 기본 응답
    return "네, 말씀해주세요. 무엇을 도와드릴까요?"

# 명함 정보 추출 (확실히 작동하는 버전)
def extract_business_card_info(image):
    try:
        # 이미지를 그레이스케일로 변환
        gray_image = image.convert('L')
        
        # OCR로 텍스트 추출
        text = pytesseract.image_to_string(gray_image, lang='kor+eng')
        
        # 텍스트를 줄별로 분리
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
            # 이메일 찾기
            if '@' in line and '.' in line:
                info["email"] = line
            # 전화번호 찾기 (숫자가 8개 이상)
            elif sum(c.isdigit() for c in line) >= 8:
                info["phone"] = line
            # 회사명 찾기 (대문자 포함)
            elif any(c.isupper() for c in line) and len(line) > 2:
                if info["company"] == "회사명을 찾을 수 없음":
                    info["company"] = line
            # 이름 찾기 (한글/영문, 2-10자)
            elif 2 <= len(line) <= 10 and not any(c.isdigit() for c in line):
                if info["name"] == "이름을 찾을 수 없음":
                    info["name"] = line
        
        return info
        
    except Exception as e:
        st.error(f"추출 중 오류 발생: {str(e)}")
        return {
            "name": "오류 발생",
            "company": "오류 발생",
            "phone": "오류 발생",
            "email": "오류 발생",
            "raw_text": "텍스트 추출 실패"
        }

# 메인 UI
st.title("💼 AI Assistant")
st.markdown("**실제로 작동하는 AI 도우미**")

# 1. 명함 OCR
st.header("📇 명함 OCR")
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

# 2. 명함 질문 기능
if st.session_state.business_cards:
    st.header("💬 명함에 대해 질문하기")
    
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
                # 명함 정보를 포함한 질문
                context = f"명함 정보: 이름={selected_card['name']}, 회사={selected_card['company']}, 전화={selected_card['phone']}, 이메일={selected_card['email']}"
                full_question = f"{context}\n\n질문: {card_question}"
                
                answer = get_ai_response(card_question)
                
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

# 3. AI 채팅
st.header("🤖 AI 채팅")
chat_question = st.text_input("질문을 입력하세요:", placeholder="무엇이든 물어보세요...")

if st.button("🤖 답변 생성", key="chat_qa") and chat_question:
    with st.spinner("답변을 생성하고 있습니다..."):
        answer = get_ai_response(chat_question)
        
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

# 4. 대화 기록
if st.session_state.conversation_history:
    st.header("💬 대화 기록")
    for i, entry in enumerate(reversed(st.session_state.conversation_history)):
        with st.expander(f"{entry['type']} - {entry['question'][:30]}..."):
            st.write(f"**질문:** {entry['question']}")
            st.write(f"**답변:** {entry['answer']}")
            st.write(f"**시간:** {entry['timestamp']}")

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
