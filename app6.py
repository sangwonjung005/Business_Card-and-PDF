import streamlit as st
from PyPDF2 import PdfReader
import io
import time

# 페이지 설정
st.set_page_config(
    page_title="PDF AI 도우미",
    page_icon="📄",
    layout="wide"
)

# 세션 상태 초기화
if "pdf_documents" not in st.session_state:
    st.session_state.pdf_documents = []

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

# 간단한 AI 답변 함수
def get_ai_answer(question, pdf_content):
    """PDF 내용을 바탕으로 AI 답변 생성"""
    try:
        # PDF 내용에서 관련 정보 찾기
        question_lower = question.lower()
        pdf_lower = pdf_content.lower()
        
        # 질문 키워드 추출
        keywords = question_lower.split()
        
        # 관련 문장 찾기
        sentences = pdf_content.split('.')
        relevant_sentences = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            # 키워드가 포함된 문장 찾기
            if any(keyword in sentence_lower for keyword in keywords if len(keyword) > 2):
                relevant_sentences.append(sentence.strip())
        
        # 답변 생성
        if relevant_sentences:
            # 관련 문장들을 조합해서 답변 생성
            answer = " ".join(relevant_sentences[:3])  # 최대 3개 문장
            if len(answer) > 500:
                answer = answer[:500] + "..."
            
            return f"**AI 답변:** {answer}"
        else:
            return f"**AI 답변:** PDF에서 '{question}'에 대한 관련 정보를 찾을 수 없습니다. 다른 질문을 해보세요."
            
    except Exception as e:
        return f"**AI 답변:** 답변 생성 중 오류가 발생했습니다: {str(e)}"

# 메인 UI
st.title("📄 PDF AI 도우미")
st.markdown("**PDF를 업로드하고 질문하세요!**")

# PDF 업로드 섹션
st.header("📤 PDF 업로드")
uploaded_pdf = st.file_uploader("PDF 파일을 선택하세요", type=['pdf'])

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
    st.header("📚 업로드된 PDF 목록")
    
    for i, pdf_doc in enumerate(st.session_state.pdf_documents):
        with st.expander(f"📄 {pdf_doc['name']} (업로드: {pdf_doc['upload_time']})"):
            st.write(f"**크기:** {pdf_doc['size']} 문자")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(f"🗑️ 삭제", key=f"delete_{i}"):
                    st.session_state.pdf_documents.pop(i)
                    st.success("PDF가 삭제되었습니다!")
                    st.rerun()
            
            with col2:
                if st.button(f"💬 질문하기", key=f"ask_{i}"):
                    st.session_state.selected_pdf_index = i

# 질문 섹션
st.header("💬 PDF에 대해 질문하기")

if st.session_state.pdf_documents:
    # PDF 선택
    if hasattr(st.session_state, 'selected_pdf_index') and st.session_state.selected_pdf_index is not None:
        selected_pdf = st.session_state.pdf_documents[st.session_state.selected_pdf_index]
        st.info(f"선택된 PDF: {selected_pdf['name']}")
    
    # 질문 입력
    question = st.text_input(
        "질문을 입력하세요:",
        placeholder="PDF 내용에 대해 질문해보세요..."
    )
    
    if st.button("🤖 답변 생성", type="primary") and question:
        with st.spinner("답변을 생성하고 있습니다..."):
            # 선택된 PDF가 있으면 해당 PDF에서, 없으면 모든 PDF에서 검색
            if hasattr(st.session_state, 'selected_pdf_index') and st.session_state.selected_pdf_index is not None:
                selected_pdf = st.session_state.pdf_documents[st.session_state.selected_pdf_index]
                answer = get_ai_answer(question, selected_pdf['content'])
            else:
                # 모든 PDF에서 검색
                all_content = "\n\n".join([doc['content'] for doc in st.session_state.pdf_documents])
                answer = get_ai_answer(question, all_content)
            
            st.markdown("---")
            st.markdown("### 🤖 AI 답변")
            st.write(answer)
            
            # PDF 내용 미리보기
            with st.expander("📄 관련 PDF 내용 보기"):
                if hasattr(st.session_state, 'selected_pdf_index') and st.session_state.selected_pdf_index is not None:
                    selected_pdf = st.session_state.pdf_documents[st.session_state.selected_pdf_index]
                    st.text_area("PDF 내용", selected_pdf['content'][:1000] + "..." if len(selected_pdf['content']) > 1000 else selected_pdf['content'], height=300)
                else:
                    st.write("모든 PDF의 내용이 검색에 사용되었습니다.")

else:
    st.info("먼저 PDF를 업로드해주세요!")

# 초기화 버튼
if st.button("🗑️ 모든 데이터 초기화"):
    st.session_state.pdf_documents = []
    if hasattr(st.session_state, 'selected_pdf_index'):
        del st.session_state.selected_pdf_index
    st.success("초기화 완료!")
    st.rerun()

# 사이드바
with st.sidebar:
    st.header("📊 통계")
    st.write(f"업로드된 PDF: {len(st.session_state.pdf_documents)}개")
    
    if st.session_state.pdf_documents:
        st.subheader("📚 PDF 목록")
        for pdf_doc in st.session_state.pdf_documents:
            st.write(f"• {pdf_doc['name']}")
            st.caption(f"크기: {pdf_doc['size']} 문자")
    
    st.markdown("---")
    st.header("💡 사용법")
    st.write("""
    1. **PDF 파일 업로드**
    2. **PDF 추가 버튼 클릭**
    3. **질문하기 버튼으로 PDF 선택**
    4. **질문 입력 후 답변 생성**
    """)
    
    st.markdown("---")
    st.header("🔧 기능")
    st.write("""
    ✅ **PDF 업로드**: 여러 PDF 저장
    ✅ **PDF별 질문**: 특정 PDF 선택
    ✅ **통합 검색**: 모든 PDF에서 검색
    ✅ **빠른 답변**: 즉시 AI 답변
    ✅ **간단한 UI**: 직관적인 인터페이스
    """)
