import streamlit as st
from PIL import Image
import pytesseract
import time
from PyPDF2 import PdfReader
import io
import re
import os

# OpenAI API 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    # 로컬 파일에서 API 키 읽기 시도
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

# OpenAI 클라이언트
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        GPT_AVAILABLE = True
    except:
        GPT_AVAILABLE = False
else:
    GPT_AVAILABLE = False

# 페이지 설정
st.set_page_config(
    page_title="명함 & PDF AI 도우미",
    page_icon="💼",
    layout="wide"
)

# 세션 상태 초기화
if "business_cards" not in st.session_state:
    st.session_state.business_cards = []
if "pdf_documents" not in st.session_state:
    st.session_state.pdf_documents = []
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# 명함 정보 추출 함수
def extract_business_card_info(image):
    """명함에서 정보 추출"""
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
        
        # 정보 추출 로직
        for line in lines:
            line = line.strip()
            
            # 이메일 찾기
            if '@' in line and '.' in line:
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, line)
                if emails:
                    info["email"] = emails[0]
            
            # 전화번호 찾기
            elif any(c.isdigit() for c in line):
                phone_pattern = r'(\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4})'
                phones = re.findall(phone_pattern, line)
                if phones:
                    clean_phone = phones[0].replace('M_', '').replace('_', '')
                    if len(clean_phone.replace('-', '').replace(' ', '')) >= 10:
                        info["phone"] = clean_phone
            
            # 회사명 찾기
            elif any(word in line for word in ['연구원', '주식회사', '(주)', 'Corp', 'Inc', 'Ltd', '기술', '전자']):
                if info["company"] == "회사명을 찾을 수 없음":
                    info["company"] = line
            
            # 직책 찾기
            elif any(word in line for word in ['센터장', '부장', '과장', '대리', '사원', 'Manager', 'Director', 'CEO', 'CTO']):
                if info["position"] == "직책을 찾을 수 없음":
                    info["position"] = line
            
            # 이름 찾기 (간단한 로직)
            elif 2 <= len(line) <= 10 and not any(c.isdigit() for c in line):
                if info["name"] == "이름을 찾을 수 없음":
                    info["name"] = line
            
            # 주소 찾기
            elif any(word in line for word in ['번길', '동', '층', '센터', '로', '길', '구', '시', '도']):
                if info["address"] == "주소를 찾을 수 없음":
                    info["address"] = line
        
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
        "size": len(pdf_text)
    }

# GPT 답변 함수
def get_gpt_answer(question, context=""):
    """GPT를 사용한 답변 생성"""
    if not GPT_AVAILABLE:
        return "**AI 답변:** GPT API가 설정되지 않았습니다. 환경변수 OPENAI_API_KEY를 설정하거나 nocommit_key.txt 파일에 API 키를 저장해주세요."
    
    try:
        if context:
            prompt = f"""다음 정보를 참고하여 질문에 답변해주세요.

참고 정보:
{context}

질문: {question}

답변:"""
        else:
            prompt = question
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        
        return f"**AI 답변:** {response.choices[0].message.content}"
        
    except Exception as e:
        return f"**AI 답변:** GPT 답변 생성 중 오류가 발생했습니다: {str(e)}"

# 로컬 AI 답변 함수 (GPT 사용 불가능할 때)
def get_local_answer(question, context=""):
    """로컬 AI 답변 - 키워드 기반"""
    responses = {
        "안녕": "안녕하세요! AI 도우미입니다. 무엇을 도와드릴까요?",
        "이름": "제 이름은 AI 도우미입니다. 반갑습니다!",
        "도움": "명함 OCR, PDF 분석, 일반 대화를 도와드릴 수 있습니다.",
        "감사": "천만에요! 더 도움이 필요하시면 언제든 말씀해주세요.",
        "시간": f"현재 시간은 {time.strftime('%Y년 %m월 %d일 %H:%M분')}입니다.",
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

# 메인 UI
st.title("💼 명함 & PDF AI 도우미")
st.markdown("**명함 OCR, PDF 분석, AI 채팅**")

# AI 상태 표시
if GPT_AVAILABLE:
    st.success("✅ GPT API 연결됨 - 고품질 AI 답변 가능")
else:
    st.warning("⚠️ GPT API 미연결 - 로컬 AI 답변 사용")

# 탭 생성
tab1, tab2, tab3, tab4 = st.tabs(["📇 명함 OCR", "📄 PDF 분석", "💬 AI 채팅", "📊 대화 기록"])

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
    st.header("📄 PDF 분석")
    st.write("PDF 파일을 업로드하고 내용에 대해 질문하세요.")
    
    # PDF 업로드
    uploaded_pdf = st.file_uploader("PDF 파일 업로드", type=['pdf'])
    
    if uploaded_pdf is not None:
        if st.button("📖 PDF 추가", type="primary"):
            with st.spinner("PDF를 읽고 있습니다..."):
                uploaded_pdf.seek(0)
                pdf_text = read_pdf(uploaded_pdf)
                
                if pdf_text:
                    uploaded_pdf.seek(0)
                    pdf_doc = create_pdf_document(uploaded_pdf, pdf_text)
                    st.session_state.pdf_documents.append(pdf_doc)
                    st.success(f"✅ PDF '{pdf_doc['name']}' 추가 완료!")
                    st.rerun()
    
    # 업로드된 PDF 목록
    if st.session_state.pdf_documents:
        st.subheader("📚 업로드된 PDF 목록")
        
        for i, pdf_doc in enumerate(st.session_state.pdf_documents):
            with st.expander(f"📄 {pdf_doc['name']} (업로드: {pdf_doc['upload_time']})"):
                st.write(f"**크기:** {pdf_doc['size']} 문자")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    if st.button(f"🗑️ 삭제", key=f"delete_pdf_{i}"):
                        st.session_state.pdf_documents.pop(i)
                        st.success("PDF가 삭제되었습니다!")
                        st.rerun()
                
                with col2:
                    if st.button(f"📖 내용 보기", key=f"view_pdf_{i}"):
                        st.text_area("PDF 내용", pdf_doc['content'][:2000] + "..." if len(pdf_doc['content']) > 2000 else pdf_doc['content'], height=300, key=f"pdf_content_{i}")
                
                with col3:
                    if st.button(f"💬 질문하기", key=f"ask_pdf_{i}"):
                        st.session_state.selected_pdf_index = i
        
        # PDF 질문
        if hasattr(st.session_state, 'selected_pdf_index') and st.session_state.selected_pdf_index is not None:
            selected_pdf = st.session_state.pdf_documents[st.session_state.selected_pdf_index]
            st.subheader(f"📝 '{selected_pdf['name']}'에 대해 질문하기")
            
            pdf_question = st.text_input(
                f"'{selected_pdf['name']}' 내용에 대해 질문하세요:",
                placeholder="PDF 내용에 대한 질문을 입력하세요..."
            )
            
            if st.button("🤖 답변 생성", key="pdf_qa") and pdf_question:
                with st.spinner("답변을 생성하고 있습니다..."):
                    # GPT 답변 생성
                    answer = get_gpt_answer(pdf_question, selected_pdf['content'][:1000])
                    
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
                
                # 검색어 전처리
                processed_query = search_query.lower()
                
                # 질문 패턴 제거
                question_patterns = [
                    "중요 부분은?", "무엇인가?", "어떤가?", "뭐야?", "뭔가?",
                    "설명해줘", "알려줘", "보여줘", "찾아줘", "검색해줘",
                    "포함한", "포함된", "관련된", "관련한", "중요부분은?"
                ]
                
                for pattern in question_patterns:
                    processed_query = processed_query.replace(pattern, "").strip()
                
                # 파일명에서 확장자 제거
                processed_query = processed_query.replace(".pdf", "").replace(".PDF", "")
                
                for pdf_doc in st.session_state.pdf_documents:
                    # 1. 파일명에서 검색
                    if processed_query.lower() in pdf_doc['name'].lower():
                        search_results.append({
                            "pdf_name": pdf_doc['name'],
                            "context": f"파일명에서 '{processed_query}' 발견",
                            "position": "파일명",
                            "match_type": "파일명"
                        })
                        continue
                    
                    # 2. PDF 내용에서 검색
                    if processed_query.lower() in pdf_doc['content'].lower():
                        content_lower = pdf_doc['content'].lower()
                        query_pos = content_lower.find(processed_query.lower())
                        
                        if query_pos != -1:
                            start = max(0, query_pos - 150)
                            end = min(len(pdf_doc['content']), query_pos + len(processed_query) + 150)
                            context = pdf_doc['content'][start:end]
                            
                            search_results.append({
                                "pdf_name": pdf_doc['name'],
                                "context": context,
                                "position": query_pos,
                                "match_type": "내용"
                            })
                    
                    # 3. 부분 매칭 (단어 단위)
                    words = processed_query.split()
                    for word in words:
                        if len(word) > 1:
                            if word.lower() in pdf_doc['name'].lower():
                                search_results.append({
                                    "pdf_name": pdf_doc['name'],
                                    "context": f"파일명에서 '{word}' 발견",
                                    "position": "파일명",
                                    "match_type": f"파일명 단어 매칭 ('{word}')"
                                })
                                break
                            
                            if word.lower() in pdf_doc['content'].lower():
                                content_lower = pdf_doc['content'].lower()
                                word_pos = content_lower.find(word.lower())
                                
                                if word_pos != -1:
                                    start = max(0, word_pos - 100)
                                    end = min(len(pdf_doc['content']), word_pos + len(word) + 100)
                                    context = pdf_doc['content'][start:end]
                                    
                                    search_results.append({
                                        "pdf_name": pdf_doc['name'],
                                        "context": context,
                                        "position": word_pos,
                                        "match_type": f"내용 단어 매칭 ('{word}')"
                                    })
                                    break
                
                if search_results:
                    # 중복 제거
                    unique_results = []
                    seen_pdfs = set()
                    
                    for result in search_results:
                        if result['pdf_name'] not in seen_pdfs:
                            unique_results.append(result)
                            seen_pdfs.add(result['pdf_name'])
                    
                    st.success(f"✅ {len(unique_results)}개의 PDF에서 관련 내용을 찾았습니다!")
                    
                    for i, result in enumerate(unique_results):
                        with st.expander(f"📄 {result['pdf_name']} ({result['match_type']})"):
                            if result['match_type'] == "파일명":
                                st.write(f"**매칭 유형:** {result['match_type']}")
                                st.write(f"**발견 위치:** {result['context']}")
                            else:
                                st.write(f"**매칭 유형:** {result['match_type']}")
                                st.write(f"**위치:** {result['position']}번째 문자")
                                st.text_area("검색된 내용", result['context'], height=150, key=f"search_result_{i}")
                else:
                    st.warning(f"'{search_query}'와 관련된 PDF를 찾을 수 없습니다.")
                    st.info("💡 팁: 파일명이나 내용의 일부만 입력해보세요.")
    else:
        st.info("아직 업로드된 PDF가 없습니다. PDF를 업로드해보세요!")

with tab3:
    st.header("💬 AI 채팅")
    
    # 명함 질문
    if st.session_state.business_cards:
        st.subheader("📇 명함에 대해 질문하기")
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
                        # GPT 답변 사용
                        context = f"명함 정보: 이름={selected_card['name']}, 회사={selected_card['company']}, 직책={selected_card['position']}, 전화={selected_card['phone']}, 이메일={selected_card['email']}, 주소={selected_card['address']}"
                        answer = get_gpt_answer(card_question, context)
                    
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
    
    # 일반 AI 채팅
    st.subheader("🤖 일반 AI 채팅")
    chat_question = st.text_input("질문을 입력하세요:", placeholder="무엇이든 물어보세요...")
    
    if st.button("🤖 답변 생성", key="chat_qa") and chat_question:
        with st.spinner("답변을 생성하고 있습니다..."):
            # GPT 사용 가능하면 GPT, 아니면 로컬 AI
            if GPT_AVAILABLE:
                answer = get_gpt_answer(chat_question)
            else:
                answer = get_local_answer(chat_question)
            
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
    st.session_state.pdf_documents = []
    st.session_state.conversation_history = []
    if hasattr(st.session_state, 'selected_pdf_index'):
        del st.session_state.selected_pdf_index
    st.success("초기화 완료!")
    st.rerun()

# 사이드바
with st.sidebar:
    st.header("📊 통계")
    st.write(f"저장된 명함: {len(st.session_state.business_cards)}")
    st.write(f"업로드된 PDF: {len(st.session_state.pdf_documents)}개")
    st.write(f"대화 수: {len(st.session_state.conversation_history)}")
    
    if st.session_state.business_cards:
        st.subheader("📇 명함 목록")
        for card in st.session_state.business_cards:
            st.write(f"• {card['name']} - {card['company']}")
    
    if st.session_state.pdf_documents:
        st.subheader("📚 PDF 목록")
        for pdf_doc in st.session_state.pdf_documents:
            st.write(f"• {pdf_doc['name']}")
    
    st.markdown("---")
    st.header("💡 사용법")
    st.write("""
    1. **명함 이미지 업로드** → 정보 추출
    2. **PDF 파일 업로드** → 내용 분석
    3. **명함/PDF에 대해 질문** → AI 답변
    4. **일반 AI 채팅** → 자유로운 대화
    """)
    
    st.markdown("---")
    st.header("🔧 기능")
    st.write("""
    ✅ **명함 OCR**: 텍스트 추출
    ✅ **명함 질문**: 연락처, 이름, 회사, 직책 등
    ✅ **PDF 분석**: PDF 내용 분석
    ✅ **AI 채팅**: GPT 기반 대화
    ✅ **대화 기록**: 모든 대화 저장
    ✅ **API 키 지원**: 고품질 GPT 답변
    """)
