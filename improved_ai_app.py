import streamlit as st
from PIL import Image
import pytesseract

# 페이지 설정
st.set_page_config(page_title="테스트 앱", page_icon="🧪")

# 세션 상태
if "test_mode" not in st.session_state:
    st.session_state.test_mode = True

st.title("🧪 테스트 앱")
st.write("**기본 기능 테스트**")

# 1. 간단한 OCR 테스트
st.header("📇 OCR 테스트")
uploaded_file = st.file_uploader("이미지 업로드", type=['png', 'jpg', 'jpeg'])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="업로드된 이미지")
    
    if st.button("🔍 텍스트 추출"):
        try:
            # 그레이스케일 변환
            gray = image.convert('L')
            
            # OCR 실행
            text = pytesseract.image_to_string(gray, lang='kor+eng')
            
            st.success("✅ OCR 성공!")
            st.subheader("추출된 텍스트:")
            st.text_area("텍스트", text, height=200)
            
            # 간단한 정보 추출
            lines = text.split('\n')
            st.subheader("줄별 분석:")
            for i, line in enumerate(lines):
                if line.strip():
                    st.write(f"줄 {i+1}: {line.strip()}")
                    
        except Exception as e:
            st.error(f"OCR 오류: {str(e)}")

# 2. AI 응답 테스트
st.header("🤖 AI 응답 테스트")
question = st.text_input("질문 입력:")

if st.button("답변 생성") and question:
    # 하드코딩된 응답
    responses = {
        "안녕": "안녕하세요! 테스트 앱입니다.",
        "테스트": "테스트가 성공적으로 작동하고 있습니다!",
        "ocr": "OCR 기능이 정상 작동합니다.",
        "ai": "AI 응답 기능이 정상 작동합니다."
    }
    
    answer = "기본 응답: 질문을 받았습니다."
    for key, response in responses.items():
        if key in question:
            answer = response
            break
    
    st.success("✅ AI 응답 성공!")
    st.write(f"**질문:** {question}")
    st.write(f"**답변:** {answer}")

# 3. 상태 확인
st.header("📊 상태 확인")
st.write(f"**테스트 모드:** {st.session_state.test_mode}")
st.write(f"**Streamlit 버전:** {st.__version__}")

# 4. 간단한 계산기 테스트
st.header("🧮 계산기 테스트")
num1 = st.number_input("숫자 1:", value=0)
num2 = st.number_input("숫자 2:", value=0)

if st.button("계산"):
    result = num1 + num2
    st.success(f"✅ 계산 성공: {num1} + {num2} = {result}")

st.markdown("---")
st.write("**이 테스트 앱이 작동하면 기본 기능은 정상입니다.**")
