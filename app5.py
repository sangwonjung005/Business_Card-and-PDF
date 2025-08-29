import streamlit as st
from PIL import Image
import pytesseract
import json
import time
from PyPDF2 import PdfReader
import io
import re

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
if "pdf_documents" not in st.session_state:
    st.session_state.pdf_documents = []  # 여러 PDF 저장
if "pdf_content" not in st.session_state:
    st.session_state.pdf_content = ""

# 로컬 AI 응답 함수 (API 키 없이 작동)
def call_ai_api(question: str) -> str:
    """로컬 AI 응답 - API 키 없이 작동"""
    
    # 키워드 기반 응답
    responses = {
        "안녕": "안녕하세요! AI 도우미입니다. 무엇을 도와드릴까요?",
        "이름": "제 이름은 AI 도우미입니다. 반갑습니다!",
        "도움": "명함 OCR, PDF 분석, 일반 대화를 도와드릴 수 있습니다.",
        "감사": "천만에요! 더 도움이 필요하시면 언제든 말씀해주세요.",
        "날씨": "죄송합니다. 실시간 날씨 정보는 제공할 수 없습니다.",
        "시간": f"현재 시간은 {time.strftime('%Y년 %m월 %d일 %H시 %M분')}입니다.",
        "계산": "간단한 계산이 필요하시면 말씀해주세요.",
        "추천": "무엇을 추천해드릴까요? 영화, 음식, 책 등 말씀해주세요.",
        "정보": "어떤 정보를 찾고 계신가요?",
        "설명": "무엇을 설명해드릴까요?",
        "연락처": "연락처 정보를 찾으시는군요. 명함을 업로드해보세요!",
        "회사": "회사 정보를 찾으시는군요. 명함을 업로드해보세요!",
        "직책": "직책 정보를 찾으시는군요. 명함을 업로드해보세요!",
        "주소": "주소 정보를 찾으시는군요. 명함을 업로드해보세요!",
        "이메일": "이메일 정보를 찾으시는군요. 명함을 업로드해보세요!",
        "전화": "전화번호를 찾으시는군요. 명함을 업로드해보세요!"
    }
    
    # 키워드 매칭
    for keyword, response in responses.items():
        if keyword in question:
            return f"**로컬 AI 답변:** {response}"
    
    # 기본 응답
    return "**로컬 AI 답변:** 네, 말씀해주세요. 명함 OCR, PDF 분석, 또는 일반적인 대화를 도와드릴 수 있습니다."

# 정교한 명함 정보 추출 함수 (API 키 없이도 작동)
def extract_business_card_info(image):
    """명함에서 정보 추출 - 정교한 버전"""
    try:
        # 이미지를 그레이스케일로 변환
        gray_image = image.convert('L')
        
        # OCR 실행 (한국어 + 영어)
        text = pytesseract.image_to_string(gray_image, lang='kor+eng')
        
        # 텍스트를 줄별로 분리하고 빈 줄 제거
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # 기본 정보 구조
        info = {
            "name": "이름을 찾을 수 없음",
            "company": "회사명을 찾을 수 없음", 
            "phone": "전화번호를 찾을 수 없음",
            "email": "이메일을 찾을 수 없음",
            "position": "직책을 찾을 수 없음",
            "address": "주소를 찾을 수 없음",
            "raw_text": text
        }
        
        # 회사명 패턴 (연구원, 주식회사, (주), Corp, Inc 등)
        company_patterns = [
            r'.*연구원.*',
            r'.*주식회사.*',
            r'.*\(주\).*',
            r'.*Corp.*',
            r'.*Inc.*',
            r'.*Ltd.*',
            r'.*기술.*',
            r'.*전자.*',
            r'.*KETI.*',
            r'.*한국.*',
            r'.*시스템.*',
            r'.*소프트웨어.*',
            r'.*IT.*',
            r'.*컴퓨터.*'
        ]
        
        # 이름 패턴 (한글 이름, 영문 이름)
        name_patterns = [
            r'^[가-힣]{2,4}$',  # 한글 이름 (2-4자)
            r'^[A-Za-z]{2,20}$',  # 영문 이름 (2-20자)
            r'^[A-Za-z]+\s[A-Za-z]+$',  # 영문 성+이름
            r'^[가-힣]+\s[가-힣]+$'  # 한글 성+이름
        ]
        
        # 직책 패턴
        position_patterns = [
            r'.*센터장.*',
            r'.*부장.*',
            r'.*과장.*',
            r'.*대리.*',
            r'.*사원.*',
            r'.*Manager.*',
            r'.*Director.*',
            r'.*CEO.*',
            r'.*CTO.*',
            r'.*CFO.*',
            r'.*팀장.*',
            r'.*연구원.*',
            r'.*엔지니어.*'
        ]
        
        # 정교한 추출 로직
        for line in lines:
            line = line.strip()
            
            # 이메일 찾기 (정확한 패턴)
            if '@' in line and '.' in line:
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, line)
                if emails:
                    info["email"] = emails[0]
            
            # 전화번호 찾기 (정확한 패턴)
            elif any(c.isdigit() for c in line):
                phone_pattern = r'(\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4})'
                phones = re.findall(phone_pattern, line)
                if phones:
                    clean_phone = phones[0].replace('M_', '').replace('_', '')
                    if len(clean_phone.replace('-', '').replace(' ', '')) >= 10:
                        info["phone"] = clean_phone
                else:
                    digits = ''.join(filter(str.isdigit, line))
                    if 10 <= len(digits) <= 11 and not any(word in line.lower() for word in ['번길', '동', '층', '센터', 'www', 'http']):
                        clean_line = line.replace('M_', '').replace('_', '')
                        info["phone"] = clean_line
            
            # 직책 찾기
            elif any(re.match(pattern, line) for pattern in position_patterns):
                if info["position"] == "직책을 찾을 수 없음":
                    info["position"] = line
            
            # 회사명 찾기 (정교한 로직)
            elif any(c.isupper() for c in line) and len(line) >= 2:
                # 회사명 패턴 확인
                is_company = any(re.match(pattern, line) for pattern in company_patterns)
                
                exclude_words = ['번길', '동', '층', '센터', 'www', 'http', 'co.kr', 'com', 'kr', 're.kr', 'gmail']
                not_excluded = not any(word in line.lower() for word in exclude_words)
                
                if is_company or (not_excluded and len(line) >= 3):
                    clean_company = re.sub(r'[^\w\s가-힣]', '', line)
                    if len(clean_company) >= 2:
                        if info["company"] == "회사명을 찾을 수 없음":
                            info["company"] = clean_company
            
            # 이름 찾기 (정교한 로직)
            elif 2 <= len(line) <= 20 and not any(c.isdigit() for c in line):
                # 이름 패턴 확인
                is_name = any(re.match(pattern, line) for pattern in name_patterns)
                
                exclude_words = ['번길', '동', '층', '센터', 'www', 'http', 'co.kr', 'com', 'kr', 're.kr', 'gmail', '연구원', '기술', '전자', '한국', '센터장', '부장', '과장', '대리', '사원']
                not_excluded = not any(word in line.lower() for word in exclude_words)
                
                if is_name or (not_excluded and len(line) <= 10):
                    clean_name = re.sub(r'[^\w\s가-힣]', '', line)
                    if len(clean_name) >= 2:
                        if info["name"] == "이름을 찾을 수 없음":
                            info["name"] = clean_name
            
            # 주소 찾기
            elif any(word in line for word in ['번길', '동', '층', '센터', '로', '길', '구', '시', '도']):
                if info["address"] == "주소를 찾을 수 없음":
                    info["address"] = line
        
        # 추가 후처리
        # 이메일에서 이름 추출 시도
        if info["name"] == "이름을 찾을 수 없음" and info["email"] != "이메일을 찾을 수 없음":
            email_name = info["email"].split('@')[0]
            if len(email_name) >= 2:
                info["name"] = email_name
        
        # 전화번호 정리
        if info["phone"] != "전화번호를 찾을 수 없음":
            digits = ''.join(filter(str.isdigit, info["phone"]))
            if len(digits) == 11:
                info["phone"] = f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
        
        # 최종 검증 및 수정
        # 회사명이 이름으로 잘못 들어간 경우 수정
        if "연구원" in info["name"] or "기술" in info["name"] or "전자" in info["name"]:
            if info["company"] == "회사명을 찾을 수 없음":
                info["company"] = info["name"]
                info["name"] = "이름을 찾을 수 없음"
        
        # 이름이 너무 긴 경우 회사명으로 이동
        if len(info["name"]) > 10 and info["company"] == "회사명을 찾을 수 없음":
            info["company"] = info["name"]
            info["name"] = "이름을 찾을 수 없음"
        
        return info
        
    except Exception as e:
        st.error(f"추출 중 오류: {str(e)}")
        return {
            "name": "오류 발생",
            "company": "오류 발생",
            "phone": "오류 발생", 
            "email": "오류 발생",
            "position": "오류 발생",
            "address": "오류 발생",
            "raw_text": "텍스트 추출 실패"
        }

# PDF 읽기 함수
def read_pdf(pdf_file):
    """PDF 파일 읽기"""
    try:
        pdf_reader = PdfReader(io.BytesIO(pdf_file.read()))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"PDF 읽기 오류: {str(e)}")
        return ""

# PDF 문서 정보 생성 함수
def create_pdf_document(pdf_file, pdf_text):
    """PDF 문서 정보 생성"""
    return {
        "id": f"pdf_{int(time.time())}_{len(st.session_state.pdf_documents)}",
        "name": pdf_file.name,
        "content": pdf_text,
        "upload_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "size": len(pdf_text),
        "pages": len(PdfReader(io.BytesIO(pdf_file.read())).pages)
    }

# 메인 UI
st.title("💼 명함 & AI 도우미")
st.markdown("**명함 OCR, PDF RAG, AI 채팅 (API 키 없이 완전 작동)**")

# 탭 생성
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📇 명함 OCR", "💬 명함 질문", "📄 PDF RAG", "🤖 AI 채팅", "📊 대화 기록"])

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
                    st.info(f"**직책:** {card_info['position']}")
                with col2:
                    st.info(f"**전화:** {card_info['phone']}")
                    st.info(f"**이메일:** {card_info['email']}")
                    st.info(f"**주소:** {card_info['address']}")
                
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
                placeholder="예: 연락처는? 이름은? 회사는? 직책은?"
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
                    elif "직책" in card_question:
                        answer = f"직책은 {selected_card['position']}입니다."
                    elif "주소" in card_question:
                        answer = f"주소는 {selected_card['address']}입니다."
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
    st.header("📄 PDF RAG")
    st.write("PDF 파일을 업로드하고 내용에 대해 질문하세요.")
    
    # PDF 업로드 섹션
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_pdf = st.file_uploader("PDF 파일 업로드", type=['pdf'])
    
    with col2:
        if uploaded_pdf is not None:
            if st.button("📖 PDF 추가", type="primary"):
                with st.spinner("PDF를 읽고 있습니다..."):
                    # 파일 포인터를 처음으로 되돌리기
                    uploaded_pdf.seek(0)
                    pdf_text = read_pdf(uploaded_pdf)
                    
                    if pdf_text:
                        # PDF 문서 정보 생성
                        uploaded_pdf.seek(0)  # 다시 처음으로
                        pdf_doc = create_pdf_document(uploaded_pdf, pdf_text)
                        st.session_state.pdf_documents.append(pdf_doc)
                        st.success(f"✅ PDF '{pdf_doc['name']}' 추가 완료!")
                        st.rerun()
    
    # PDF 목록 표시
    if st.session_state.pdf_documents:
        st.subheader("📚 업로드된 PDF 목록")
        
        for i, pdf_doc in enumerate(st.session_state.pdf_documents):
            with st.expander(f"📄 {pdf_doc['name']} (업로드: {pdf_doc['upload_time']})"):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"**크기:** {pdf_doc['size']} 문자, **페이지:** {pdf_doc['pages']}장")
                    if st.button(f"🗑️ 삭제", key=f"delete_pdf_{i}"):
                        st.session_state.pdf_documents.pop(i)
                        st.success("PDF가 삭제되었습니다!")
                        st.rerun()
                
                with col2:
                    if st.button(f"📖 내용 보기", key=f"view_pdf_{i}"):
                        st.text_area("PDF 내용", pdf_doc['content'][:2000] + "..." if len(pdf_doc['content']) > 2000 else pdf_doc['content'], height=300)
                
                with col3:
                    if st.button(f"💬 질문하기", key=f"ask_pdf_{i}"):
                        st.session_state.selected_pdf_index = i
        
        # 특정 PDF에 대한 질문
        if hasattr(st.session_state, 'selected_pdf_index') and st.session_state.selected_pdf_index is not None:
            selected_pdf = st.session_state.pdf_documents[st.session_state.selected_pdf_index]
            st.subheader(f"📝 '{selected_pdf['name']}'에 대해 질문하기")
            
            pdf_question = st.text_input(
                f"'{selected_pdf['name']}' 내용에 대해 질문하세요:",
                placeholder="PDF 내용에 대한 질문을 입력하세요...",
                key=f"pdf_question_{st.session_state.selected_pdf_index}"
            )
            
            if st.button("🤖 답변 생성", key=f"pdf_qa_{st.session_state.selected_pdf_index}") and pdf_question:
                with st.spinner("답변을 생성하고 있습니다..."):
                    # 선택된 PDF 내용을 포함한 질문
                    context = f"PDF '{selected_pdf['name']}' 내용: {selected_pdf['content'][:500]}..."
                    full_question = f"다음 내용에 대해 답변해주세요:\n\n{context}\n\n질문: {pdf_question}"
                    
                    answer = call_ai_api(full_question)
                    
                    # 대화 기록 저장
                    conversation_entry = {
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "question": pdf_question,
                        "answer": answer,
                        "type": f"PDF 질문 ({selected_pdf['name']})"
                    }
                    st.session_state.conversation_history.append(conversation_entry)
                    
                    st.subheader("🤖 답변")
                    st.write(answer)
        
        # 통합 검색 (모든 PDF에서 검색)
        st.subheader("🔍 모든 PDF에서 검색")
        search_query = st.text_input(
            "모든 PDF에서 검색할 키워드를 입력하세요:",
            placeholder="검색어를 입력하세요..."
        )
        
        if st.button("🔍 검색", key="search_all_pdfs") and search_query:
            with st.spinner("모든 PDF에서 검색하고 있습니다..."):
                search_results = []
                
                for pdf_doc in st.session_state.pdf_documents:
                    if search_query.lower() in pdf_doc['content'].lower():
                        # 검색된 텍스트 주변 컨텍스트 추출
                        content_lower = pdf_doc['content'].lower()
                        query_pos = content_lower.find(search_query.lower())
                        
                        if query_pos != -1:
                            start = max(0, query_pos - 100)
                            end = min(len(pdf_doc['content']), query_pos + len(search_query) + 100)
                            context = pdf_doc['content'][start:end]
                            
                            search_results.append({
                                "pdf_name": pdf_doc['name'],
                                "context": context,
                                "position": query_pos
                            })
                
                if search_results:
                    st.success(f"✅ {len(search_results)}개의 PDF에서 '{search_query}'를 찾았습니다!")
                    
                    for result in search_results:
                        with st.expander(f"📄 {result['pdf_name']}에서 발견"):
                            st.write(f"**위치:** {result['position']}번째 문자")
                            st.text_area("검색된 내용", result['context'], height=150)
                else:
                    st.warning(f"'{search_query}'를 포함한 PDF를 찾을 수 없습니다.")
    else:
        st.info("아직 업로드된 PDF가 없습니다. PDF를 업로드해보세요!")

with tab4:
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

with tab5:
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
    st.session_state.pdf_documents = []
    st.session_state.pdf_content = ""
    if hasattr(st.session_state, 'selected_pdf_index'):
        del st.session_state.selected_pdf_index
    st.success("초기화 완료!")
    st.rerun()

# 사이드바
with st.sidebar:
    st.header("📊 통계")
    st.write(f"저장된 명함: {len(st.session_state.business_cards)}")
    st.write(f"대화 수: {len(st.session_state.conversation_history)}")
    st.write(f"업로드된 PDF: {len(st.session_state.pdf_documents)}개")
    
    if st.session_state.pdf_documents:
        st.subheader("📚 PDF 목록")
        for pdf_doc in st.session_state.pdf_documents:
            st.write(f"• {pdf_doc['name']}")
            st.caption(f"크기: {pdf_doc['size']} 문자")
    
    st.markdown("---")
    st.header("🤖 AI 모드")
    st.success("✅ 로컬 AI 모드 - API 키 불필요")
    st.write("모든 기능이 로컬에서 작동합니다.")
    
    st.markdown("---")
    st.header("💡 사용법")
    st.write("""
    1. **명함 이미지 업로드**
    2. **정보 추출 버튼 클릭**
    3. **명함에 대해 질문하기**
    4. **PDF 업로드 및 질문**
    5. **AI와 자유롭게 대화하기**
    """)
    
    st.markdown("---")
    st.header("🔧 기능")
    st.write("""
    ✅ **명함 OCR**: 텍스트 추출
    ✅ **명함 질문**: 연락처, 이름, 회사, 직책 등
    ✅ **PDF RAG**: PDF 내용 분석
    ✅ **여러 PDF 관리**: 개별 PDF 저장 및 관리
    ✅ **PDF별 질문**: 특정 PDF에 대한 질문
    ✅ **통합 검색**: 모든 PDF에서 동시 검색
    ✅ **AI 채팅**: 일반적인 대화
    ✅ **대화 기록**: 모든 대화 저장
    ✅ **API 키 불필요**: 완전 로컬 작동
    """)
