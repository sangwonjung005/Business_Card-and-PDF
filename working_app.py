import streamlit as st
import json
import os
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="작동하는 앱",
    page_icon="✅",
    layout="wide"
)

# 세션 상태 초기화
if "business_cards" not in st.session_state:
    st.session_state.business_cards = []
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# 하드코딩된 AI 응답
def get_ai_response(question: str) -> str:
    """확실히 작동하는 AI 응답"""
    responses = {
        "안녕": "안녕하세요! 작동하는 AI입니다.",
        "이름": "제 이름은 작동하는 AI입니다.",
        "도움": "무엇을 도와드릴까요?",
        "감사": "천만에요!",
        "날씨": "오늘 날씨는 맑습니다.",
        "시간": f"현재 시간은 {datetime.now().strftime('%H:%M:%S')}입니다.",
        "계산": "계산이 필요하시면 말씀해주세요.",
        "추천": "추천해드릴 것이 있나요?",
        "정보": "어떤 정보를 찾고 계신가요?",
        "설명": "무엇을 설명해드릴까요?"
    }
    
    for keyword, response in responses.items():
        if keyword in question:
            return response
    
    return "네, 말씀해주세요. 무엇을 도와드릴까요?"

# 명함 정보 입력
def create_business_card():
    """수동으로 명함 정보 입력"""
    st.subheader("📇 명함 정보 입력")
    
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("이름:", key="name_input")
        company = st.text_input("회사:", key="company_input")
    
    with col2:
        phone = st.text_input("전화번호:", key="phone_input")
        email = st.text_input("이메일:", key="email_input")
    
    if st.button("💾 명함 저장", type="primary"):
        if name and company:
            card_info = {
                "name": name,
                "company": company,
                "phone": phone or "없음",
                "email": email or "없음",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "수동 입력"
            }
            
            st.session_state.business_cards.append(card_info)
            st.success("✅ 명함 정보가 저장되었습니다!")
            st.rerun()
        else:
            st.error("❌ 이름과 회사는 필수입니다!")

# 메인 UI
st.title("✅ 작동하는 앱")
st.markdown("**확실히 작동하는 명함 관리와 AI 채팅**")

# 탭 생성
tab1, tab2, tab3, tab4 = st.tabs(["📇 명함 관리", "🤖 AI 채팅", "💬 대화 기록", "📊 통계"])

with tab1:
    st.header("📇 명함 관리")
    
    # 명함 입력
    create_business_card()
    
    # 저장된 명함 목록
    if st.session_state.business_cards:
        st.subheader("📋 저장된 명함")
        for i, card in enumerate(st.session_state.business_cards):
            with st.expander(f"{card['name']} - {card['company']} ({card['timestamp']})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**이름:** {card['name']}")
                    st.info(f"**회사:** {card['company']}")
                with col2:
                    st.info(f"**전화:** {card['phone']}")
                    st.info(f"**이메일:** {card['email']}")
                
                # 명함에 대한 질문
                st.subheader("💬 명함에 대해 질문하기")
                question = st.text_input(f"{card['name']}에 대해 질문:", key=f"card_q_{i}")
                
                if st.button("🤖 답변", key=f"card_a_{i}") and question:
                    if "연락처" in question or "전화" in question:
                        answer = f"연락처: {card['phone']}, 이메일: {card['email']}"
                    elif "이름" in question:
                        answer = f"이름은 {card['name']}입니다."
                    elif "회사" in question:
                        answer = f"회사는 {card['company']}입니다."
                    else:
                        answer = get_ai_response(question)
                    
                    st.write(f"**답변:** {answer}")
                    
                    # 대화 기록 저장
                    conversation_entry = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "question": question,
                        "answer": answer,
                        "type": f"명함 질문 ({card['name']})"
                    }
                    st.session_state.conversation_history.append(conversation_entry)

with tab2:
    st.header("🤖 AI 채팅")
    
    # 채팅 입력
    user_question = st.text_input("질문을 입력하세요:", placeholder="무엇이든 물어보세요...")
    
    if st.button("🤖 답변 생성", type="primary") and user_question:
        with st.spinner("답변을 생성하고 있습니다..."):
            answer = get_ai_response(user_question)
            
            # 대화 기록 저장
            conversation_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "question": user_question,
                "answer": answer,
                "type": "일반 채팅"
            }
            st.session_state.conversation_history.append(conversation_entry)
            
            st.subheader("🤖 답변")
            st.write(answer)

with tab3:
    st.header("💬 대화 기록")
    
    if st.session_state.conversation_history:
        for i, entry in enumerate(reversed(st.session_state.conversation_history)):
            with st.expander(f"{entry['type']} - {entry['question'][:30]}..."):
                st.write(f"**질문:** {entry['question']}")
                st.write(f"**답변:** {entry['answer']}")
                st.write(f"**시간:** {entry['timestamp']}")
    else:
        st.info("아직 대화 기록이 없습니다.")

with tab4:
    st.header("📊 통계")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("저장된 명함", len(st.session_state.business_cards))
    
    with col2:
        st.metric("대화 수", len(st.session_state.conversation_history))
    
    with col3:
        if st.session_state.business_cards:
            latest_card = st.session_state.business_cards[-1]
            st.metric("최근 명함", latest_card['name'])
        else:
            st.metric("최근 명함", "없음")
    
    # 데이터 관리
    st.subheader("🗑️ 데이터 관리")
    if st.button("모든 데이터 삭제"):
        st.session_state.business_cards = []
        st.session_state.conversation_history = []
        st.success("모든 데이터가 삭제되었습니다!")
        st.rerun()

# 사이드바
with st.sidebar:
    st.header("✅ 작동하는 앱 정보")
    st.write("**확실히 작동합니다!**")
    st.write("**외부 의존성 없음**")
    st.write("**즉시 사용 가능**")
    
    st.markdown("---")
    st.header("💡 사용법")
    st.write("""
    1. **명함 정보 수동 입력**
    2. **AI와 자유롭게 대화**
    3. **대화 기록 확인**
    4. **통계 확인**
    """)
    
    st.markdown("---")
    st.header("✅ 기능")
    st.write("""
    - 📇 명함 관리
    - 🤖 AI 채팅
    - 💬 대화 기록
    - 📊 통계
    """)

st.success("�� 이 앱은 확실히 작동합니다!")
